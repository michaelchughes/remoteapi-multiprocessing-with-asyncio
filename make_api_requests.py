import argparse
import json
import sys
import os
import logging
import multiprocessing
import pandas as pd
import numpy as np
import time

from WorkerAsync import WorkerAsync
from WorkerSync import WorkerSync

logging.basicConfig(
    format="%(asctime)s %(levelname)5s:%(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("Ticker")

def parse_cli_args_and_load_config():
    ''' Parse args from command line and load JSON config
    '''
    parser = argparse.ArgumentParser(
        description='Compare sync vs async parallel processing of remote api requests')

    parser.add_argument('--mode',
        default='sync',
        choices=['sync', 'async'],
        help='Mode of processing API requests within one worker')
    parser.add_argument('--num_api_requests',
        type=int,
        default=10,
        help='Number of requests to perform')
    parser.add_argument('--max_requests_per_period',
        type=int,
        default=25, 
        help='Rate limit on number of API requests allowed per period')
    parser.add_argument('--period_duration_sec',
        type=float,
        default=5.0,
        help="Duration of period (in seconds) used for rate-limiting for remote API")
    parser.add_argument('--num_workers',
        type=int,
        default=1,
        help='Number of worker processes to run in parallel')
    parser.add_argument('--config_json_file',
        type=str,
        default='config_api_requests.json',
        help='Path to config file with fields base_url, params, and list_of_api_requests')
    args = parser.parse_args()

    conf_dict = {}
    with open(args.config_json_file, 'r') as f:
        conf_dict = json.load(f)

    argdict = args.__dict__
    argdict.update(conf_dict)
    return argdict

def summarize_categorical_column(my_df, column_name, num_uvals_to_display=-1):
    """ Make readable string of most common entries in a column of dataframe
    """
    all_vals = my_df[column_name].values.copy()
    try:
        u_vals_and_nans_U, u_rowids_U, u_count_U = np.unique(all_vals, return_index=1, return_counts=1)
        finite_bmask_U = pd.notnull(u_vals_and_nans_U)

    except TypeError:
        # Handle mix of strings and nans
        finite_bmask_A = pd.notnull(all_vals)
        nan_bmask_A = np.logical_not(finite_bmask_A)
        all_vals = np.asarray(all_vals, dtype=object)
        all_vals[nan_bmask_A] = 'NaN'
        u_vals_and_nans_U, u_rowids_U, u_count_U = np.unique(all_vals, return_index=1, return_counts=1)

        finite_bmask_U = np.ones(u_count_U.size, dtype=bool)
        for uu,rr in enumerate(u_rowids_U):
            if nan_bmask_A[rr]:
                finite_bmask_U[uu] = False

    u_vals_U = u_vals_and_nans_U[finite_bmask_U].copy()
    u_count_U = u_count_U[finite_bmask_U].copy()

    sort_ids = u_count_U.argsort(axis=-1)[::-1] # descending order
    u_vals_U = u_vals_U[sort_ids]
    u_count_U = u_count_U[sort_ids]

    s_list = list()
    if num_uvals_to_display < 0:
        num_uvals_to_display = len(u_vals_U)
    for uu in range(num_uvals_to_display):
        s = '%5d %4.0f%% %20s' % (u_count_U[uu], 100 * u_count_U[uu]/np.sum(u_count_U), u_vals_U[uu])
        s_list.append(s)
    return '\n'.join(s_list)

def main(
        num_workers=1,
        num_api_requests=10,
        mode='sync',
        list_of_api_requests=None,
        params_for_api_request=None,
        base_url='',
        period_duration_sec=1.0,
        max_requests_per_period=1000,
        **unused_kwargs,
        ):
    # Start many workers multiprocessing limited by the available cores
    logger.info(f'[main] Performing {num_api_requests} requests with {num_workers} workers')
    logger.info(f'[main] Obeying rate limit of {max_requests_per_period} requests in each {period_duration_sec} second window')

    start_time = time.perf_counter()

    # Task queue used to make tasks available to workers
    # Each item will be a string or None
    tq = multiprocessing.JoinableQueue()
    
    # Result queue aggregates results from all workers
    # Each result will be a tuple (ticker,value,long_name) or (ticker,-1, 'FAIL')
    rq = multiprocessing.Queue()

    # Launch workers
    if mode == 'async':
        WConstructor = WorkerAsync
    else:
        WConstructor = WorkerSync
    worker_list = list()

    max_req_W = max_requests_per_period // num_workers * np.ones(num_workers, dtype=np.int32)
    n_leftover = int(max_requests_per_period - max_req_W[0] * num_workers)
    max_req_W[:n_leftover] += 1
    for ww in range(num_workers):
        worker = WConstructor(tq, rq, base_url, params_for_api_request,
            logger, period_duration_sec, max_req_W[ww])
        worker.start()
        worker_list.append(worker)

    # Enter tasks into the task queue
    for idx, task_str in enumerate(list_of_api_requests):
        if idx >= num_api_requests:
            break
        tq.put(task_str)

    # Add sentinel value 'none' indicating completion
    for _ in range(num_workers):
        tq.put(None)

    # Go do the work!
    logger.info(f'[main] Tasks queued!')
    tq.join()

    # Once all work is done, log results
    result_list = [rq.get() for _ in range(num_api_requests)]
    success_list = [row for row in result_list if row[2].count('FAIL')==0]
    result_df = pd.DataFrame(success_list, columns=['symbol', 'price', 'long_name'])

    fail_list = [(row[0],row[2]) for row in result_list if row[2].count('FAIL')==1]
    fail_df = pd.DataFrame(fail_list, columns=['symbol', 'err_msg'])

    duration_in_sec = time.perf_counter() - start_time

    logger.info("[main] Done after %.1f seconds: %d/%d requests succeeded with avg price $%.2f" % (
        duration_in_sec, len(success_list), num_api_requests, result_df['price'].mean()))

    msg_list = list()

    if fail_df.shape[0] == 0:
        pass
    else:
        msg_list.append("Analysing the %d requests that failed...\n" % fail_df.shape[0])
        msg_list.append("Frequency of Error Types")
        msg_list.append("----------------------")
        msg_list.append(summarize_categorical_column(fail_df, 'err_msg'))

        msg_list.append("Example errors")
        msg_list.append("--------------")
        msg_list.append(fail_df.head(15).to_string(index=False))
        if fail_df.shape[0] > 15:
            msg_list.append("...")
            msg_list.append(fail_df.iloc[15:].tail(10).to_string(header=False, index=False))

    for m in msg_list:
        print(m)

if __name__ == '__main__':
    main(**parse_cli_args_and_load_config())
