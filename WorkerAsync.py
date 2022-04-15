import asyncio
import sys
import os
import logging

from aiohttp import ClientSession

from WorkerABC import WorkerABC

class WorkerAsync(WorkerABC):

    async def do_api_request(self, ticker: str, session: ClientSession) -> str:
        """ Make http GET request to fetch ticker data.
        """
        kwargs = self.make_api_call_ingredients(ticker)
        resp = await session.get(**kwargs)
        if resp.status != 200:
            return self.process_bad_response_from_api(ticker, resp.status)
        else:
            text_result = await resp.text()
            return self.process_response_from_api(ticker, text_result)

    async def process_many_api_requests_async(self, tickers: list) -> None:
        """ Perform many requests concurrently to fetch ticker info
        """
        async with ClientSession() as session:
            tasks = []
            for t in tickers:
                tasks.append(self.do_api_request(ticker=t, session=session))
            await asyncio.gather(*tasks)

    def process_many_api_requests(self, ticker_symbols):
        asyncio.run(self.process_many_api_requests_async(ticker_symbols))

