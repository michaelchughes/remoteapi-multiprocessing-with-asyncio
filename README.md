Code for making many requests to a remote API and processing the results, *fast*

For this demo, the task of interest is to ask for the latest close price of many stocks, and to aggregate the results.
Each remote API request queries one stock (by ticker symbol), and processes the results.

Naturally, nothing here is really specific to the stock example. Any remote API request can be accommodated.

Features:

* Can flexibly use multiple processes in parallel, each handling separate requests (via `multiprocessing` package)
* Can use `asyncio` to avoid stalling while waiting for the remote server to respond
* Can obey a rate limit: You can specify a maximum number of requests allowed in each X second period

## Usage

To perform 500 requests among 2 workers, each in "syncronous" mode (wait for HTTP get request to complete before moving on)

```
export XAPIKEY=<YOUR API KEY HERE>
python make_api_requests.py \
	--mode sync \
	--num_api_requests 500 \
	--num_workers 2 \
	--period_duration_sec 5.0 \
	--max_requests_per_period 22
```

We would set `--mode async` to do the same in "async" mode (no blocking on IO, uses `asyncio` Python package) 

Here, the rate limiting is set so that no more than 22 requests (across all processes) happen every 5 seconds.
That roughly yields a rate limit of 260 queries per minute (the API's max limit was 300, and we found pushing too close to that led to problems like many 429 errors).

## Example results

We tested the above script across async/sync modes and across 1, 2, and 4 workers on MCH's laptop on 2022-04-15 under a typical text-editing workload. 

At the rate limit of 22 requests per 5 second period, the *best* we could hope is for all work to be done in 113 seconds (`500 * 5/22 = 113`)

Awesomely, that's what we achieve in both asyncio and multi-worker sync settings!

Here's what we get:

<table class="c13"><tbody><tr class="c11"><td class="c10" colspan="1" rowspan="1"><p class="c0"><span class="c5">nworkers</span></p></td><td class="c7" colspan="1" rowspan="1"><p class="c0"><span class="c5">mode</span></p></td><td class="c10" colspan="1" rowspan="1"><p class="c0"><span class="c5">total time</span></p><p class="c0"><span class="c5">(sec)</span></p></td><td class="c8" colspan="1" rowspan="1"><p class="c0"><span class="c5">quality</span></p></td><td class="c2" colspan="1" rowspan="1"><p class="c0"><span class="c5">per-worker log examples</span></p></td></tr><tr class="c11"><td class="c10" colspan="1" rowspan="1"><p class="c6"><span class="c5">1</span></p></td><td class="c7" colspan="1" rowspan="1"><p class="c6"><span class="c5">sync</span></p></td><td class="c10" colspan="1" rowspan="1"><p class="c6"><span class="c12">129.9</span></p></td><td class="c8" colspan="1" rowspan="1"><p class="c0"><span class="c5">424/500 requests succeeded </span></p><p class="c0"><span class="c5">with avg price $58.92</span></p></td><td class="c2" colspan="1" rowspan="1"><p class="c0"><span class="c1">11:15:17 [WorkerSync-1] &nbsp;handling 22 requests</span></p><p class="c0"><span class="c1">11:15:22 [WorkerSync-1] completed 22 requests after 5.53 sec</span></p><p class="c0"><span class="c1">11:15:22 [WorkerSync-1] &nbsp;handling 22 requests</span></p><p class="c0"><span class="c1">11:15:28 [WorkerSync-1] completed 22 requests after 5.53 sec</span></p><p class="c0"><span class="c1">11:15:28 [WorkerSync-1] &nbsp;handling 22 requests</span></p><p class="c0"><span class="c1">11:15:33 [WorkerSync-1] completed 22 requests after 5.46 sec</span></p><p class="c0 c3"><span class="c1"></span></p></td></tr><tr class="c11"><td class="c10" colspan="1" rowspan="1"><p class="c6"><span class="c5">1</span></p></td><td class="c7" colspan="1" rowspan="1"><p class="c6"><span class="c5">async</span></p></td><td class="c10" colspan="1" rowspan="1"><p class="c6"><span class="c4">112.7</span></p></td><td class="c8" colspan="1" rowspan="1"><p class="c0"><span class="c5">411/500 requests succeeded</span></p><p class="c0"><span class="c5">with avg price $59.86</span></p></td><td class="c2" colspan="1" rowspan="1"><p class="c0"><span class="c1">11:11:36 [WorkerAsync-1] &nbsp;handling 22 requests</span></p><p class="c0"><span class="c1">11:11:37 [WorkerAsync-1] completed 22 requests after 1.28 sec</span></p><p class="c0"><span class="c1">11:11:41 [WorkerAsync-1] &nbsp;handling 22 requests</span></p><p class="c0"><span class="c1">11:11:42 [WorkerAsync-1] completed 22 requests after 1.22 sec</span></p><p class="c0"><span class="c1">11:11:46 [WorkerAsync-1] &nbsp;handling 22 requests</span></p><p class="c0"><span class="c1">11:11:48 [WorkerAsync-1] completed 22 requests after 2.24 sec</span></p></td></tr><tr class="c11"><td class="c10" colspan="1" rowspan="1"><p class="c6"><span class="c5">2</span></p></td><td class="c7" colspan="1" rowspan="1"><p class="c6"><span class="c5">sync</span></p></td><td class="c10" colspan="1" rowspan="1"><p class="c6"><span class="c4">113.1</span></p></td><td class="c8" colspan="1" rowspan="1"><p class="c0"><span class="c5">413/500 requests succeeded with avg price $58.07</span></p></td><td class="c2" colspan="1" rowspan="1"><p class="c0"><span class="c1">11:20:02 [WorkerSync-1] &nbsp;handling 11 requests</span></p><p class="c0"><span class="c1">11:20:02 [WorkerSync-2] &nbsp;handling 11 requests</span></p><p class="c0"><span class="c1">11:20:04 [WorkerSync-1] completed 11 requests after 2.15 sec</span></p><p class="c0"><span class="c1">11:20:04 [WorkerSync-2] completed 11 requests after 2.21 sec</span></p><p class="c0"><span class="c1">11:20:07 [WorkerSync-1] &nbsp;handling 11 requests</span></p><p class="c0"><span class="c1">11:20:07 [WorkerSync-2] &nbsp;handling 11 requests</span></p><p class="c0"><span class="c1">11:20:09 [WorkerSync-2] completed 11 requests after 2.04 sec</span></p><p class="c0"><span class="c1">11:20:09 [WorkerSync-1] completed 11 requests after 2.21 sec</span></p></td></tr><tr class="c11"><td class="c10" colspan="1" rowspan="1"><p class="c6"><span class="c5">2</span></p></td><td class="c7" colspan="1" rowspan="1"><p class="c6"><span class="c5">async</span></p></td><td class="c10" colspan="1" rowspan="1"><p class="c6"><span class="c4">112.7</span></p></td><td class="c8" colspan="1" rowspan="1"><p class="c0"><span class="c5">408/500 requests succeeded with avg price $59.02</span></p></td><td class="c2" colspan="1" rowspan="1"><p class="c0 c3"><span class="c1"></span></p><p class="c0"><span class="c1">11:27:20 [WorkerAsync-1] &nbsp;handling 11 requests</span></p><p class="c0"><span class="c1">11:27:20 [WorkerAsync-2] &nbsp;handling 11 requests</span></p><p class="c0"><span class="c1">11:27:21 [WorkerAsync-2] completed 11 requests after 1.29 sec</span></p><p class="c0"><span class="c1">11:27:22 [WorkerAsync-1] completed 11 requests after 2.23 sec</span></p><p class="c0"><span class="c1">11:27:25 [WorkerAsync-2] &nbsp;handling 11 requests</span></p><p class="c0"><span class="c1">11:27:25 [WorkerAsync-1] &nbsp;handling 11 requests</span></p><p class="c0"><span class="c1">11:27:26 [WorkerAsync-1] completed 11 requests after 1.28 sec</span></p><p class="c0"><span class="c1">11:27:27 [WorkerAsync-2] completed 11 requests after 2.35 sec</span></p></td></tr></tbody></table>

<a href="https://docs.google.com/document/d/e/2PACX-1vT0Ij4iezLrShJlV6zC2yOcigtUEex4xnnlqToFVoYzpr_bZdKTyKwTsi_vPEOLlHwgHH-1eRbeypr6/pub">
Google Doc Source</a>

## Acknowledgments

After looking at many possible sources, I based my approach almost completely on this blog post:

<https://medium.com/@nbasker/python-asyncio-with-multiprocessing-2595f8ee3f8>

And corresponding code: <https://github.com/nbasker/tools/tree/master/asyncioeval>

I think I've added some nice touches (rate limiting, better abstraction using WorkerAsync and WorkerSync classes, etc) but most credit about how to make multiprocessing and asyncio work together nicely is due to `nbasker`.
