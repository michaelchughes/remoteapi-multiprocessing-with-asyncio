import multiprocessing
import os
import json
import time

class WorkerABC(multiprocessing.Process):

    ''' Worker process for querying remote API
    '''

    def __init__(self, task_queue, result_queue,
                 base_url, params, logger, period_duration_sec, max_requests_per_period):
        multiprocessing.Process.__init__(self)
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.base_url = base_url
        self.params = dict(**params)
        self.logger = logger
        self.period_duration_sec = period_duration_sec
        self.max_requests_per_period = max_requests_per_period
        self.verbose = False

    def __str__(self):
        return 'Worker %s' % self.name

    def make_api_call_ingredients(self, ticker_symbol):
        tmp_params = self.params
        tmp_params['symbols'] = ticker_symbol
        if self.verbose:
            self.logger.info(f'[{self.name}] making API call for {ticker_symbol}')
        return {
            'url':self.base_url,
            'params':tmp_params,
            'headers':{
                'x-api-key': os.environ['XAPIKEY'],
                }}

    def process_bad_response_from_api(self, ticker, status):
        ''' Take bad result from remote call and store in result queue

        Returns
        -------
        None

        Post Condition
        --------------
        Tuple put into results queue
        '''
        err_msg = f'{ticker} FAILED {status}'
        self.result_queue.put((ticker, -1, 'FAILED ' + str(status)))
        if self.verbose:
            self.logger.error(f'[{self.name}] {err_msg}')

    def process_response_from_api(self, ticker, text):
        ''' Take text retrieved from remote call and store in result queue

        Returns
        -------
        None

        Post Condition
        --------------
        Tuple put into results queue
        '''
        d_json = json.loads(text)
        try:
            r = d_json['quoteResponse']['result'][0]
            result_tuple = (ticker, r['regularMarketPreviousClose'], r['longName'])
            self.result_queue.put(result_tuple)
            msg = "%s %.2f" % (ticker, result_tuple[1])
        except IndexError:
            bad_result = (ticker, -1, 'FAILED empty response')
            self.result_queue.put(bad_result)
            msg = "FAIL %s" % ticker
        except KeyError:
            bad_result = (ticker, -1, 'FAILED key error')
            self.result_queue.put(bad_result)
            msg = "FAIL %s" % ticker
        if self.verbose:
            self.logger.info(f'[{self.name}] {msg}')


    def run(self):
        ''' Define event loop to run when process's start() method called
        '''
        my_requests = []
        last_update_time = time.perf_counter() - 0.8 * self.period_duration_sec

        self.logger.info(f'[{self.name}] started with limit of {self.max_requests_per_period} requests per {self.period_duration_sec} sec')

        # Batch-process tasks from queue
        all_done_signal_received = False
        while len(my_requests) > 0 or (not all_done_signal_received):
            # Add next task from queue if available, until sentinel signal seen
            if not all_done_signal_received:
                t = self.task_queue.get()
                if t is None:
                    all_done_signal_received = True
                else:
                    my_requests.append(t)
                self.task_queue.task_done()

            # Do up to M requests, then wait to avoid rate limit
            time_since_last = time.perf_counter() - last_update_time
            waited_long_enough = time_since_last > self.period_duration_sec
            if waited_long_enough:
                cur_requests = my_requests[:self.max_requests_per_period]

                frac_of_max = 1.0 - (len(cur_requests) / self.max_requests_per_period)
                last_update_time = time.perf_counter() - frac_of_max * self.period_duration_sec

                if len(cur_requests) > 0:
                    self.logger.info(f'[{self.name}]  handling {len(cur_requests)} requests')

                    # Process these requests (either sync or async)
                    self.process_many_api_requests(cur_requests)

                    elapsed_sec = time.perf_counter() - last_update_time
                    self.logger.info(f'[{self.name}] completed {len(cur_requests)} requests after {elapsed_sec:.2f} sec')

                my_requests = my_requests[len(cur_requests):]

        assert len(my_requests) == 0
        assert all_done_signal_received