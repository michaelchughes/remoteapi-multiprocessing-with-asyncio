import requests

from WorkerABC import WorkerABC

class WorkerSync(WorkerABC):

    def process_many_api_requests(self, ticker_symbols):

        for ticker in ticker_symbols:
            kwargs = self.make_api_call_ingredients(ticker)
            resp = requests.get(**kwargs)
            if resp.status_code != requests.codes.ok:
                self.process_bad_response_from_api(ticker, resp.status_code)
            else:
                self.process_response_from_api(ticker, resp.text)
