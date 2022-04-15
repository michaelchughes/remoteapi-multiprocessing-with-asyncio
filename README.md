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

<iframe src="https://docs.google.com/document/d/e/2PACX-1vT0Ij4iezLrShJlV6zC2yOcigtUEex4xnnlqToFVoYzpr_bZdKTyKwTsi_vPEOLlHwgHH-1eRbeypr6/pub?embedded=true"></iframe>

## Acknowledgments

After looking at many possible sources, I based my approach almost completely on this blog post:

<https://medium.com/@nbasker/python-asyncio-with-multiprocessing-2595f8ee3f8>

And corresponding code: <https://github.com/nbasker/tools/tree/master/asyncioeval>

I think I've added some nice touches (rate limiting, better abstraction using WorkerAsync and WorkerSync classes, etc) but most credit about how to make multiprocessing and asyncio work together nicely is due to `nbasker`.
