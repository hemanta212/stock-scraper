from queue import deque
import json
import requests

from src import logger
from src.databases import cache_listings


class NYSE:
    def __init__(self) -> None:
        self.url = "https://www.nyse.com/api/quotes/filter"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }

    def queue(self):
        # Change post data, until you get all the stocks
        symbols_names = {}
        for i in range(1, 100):
            data = {
                "instrumentType": "EQUITY",
                "pageNumber": i,
                "sortColumn": "NORMALIZED_TICKER",
                "sortOrder": "ASC",
                "maxResultsPerPage": 1001,
                "filterToken": "",
            }
            response = requests.post(self.url, headers=self.headers, json=data)
            if response.status_code == 200:
                data = response.json()
                valid_stocks = [
                    i
                    for i in data
                    if i.get("symbolTicker")
                    and i.get("instrumentName")
                    and i["symbolTicker"] == i.get("normalizedTicker")
                    and i["micCode"] == "XNYS"
                ]
                for stock in valid_stocks:
                    symbol, name = stock["symbolTicker"], stock["instrumentName"]
                    symbols_names[symbol] = name
                # Check if last page or pagination remaining
                if len(data) < 1000:
                    break
            else:
                logger.exception(
                    f":: NYSEListing Error: {response.status_code} {response.text}"
                )
                raise Exception("Parsing listings error")

        logger.debug(f":: NYSEListing: Found {len(symbols_names)} stocks.")

        cache_listings(symbols_names)
        symbols = deque(symbols_names.keys())

        return symbols
