from collections import deque
from typing import Dict

import requests

from src import logger
from src.databases import cache_listings


class NYSE:
    def __init__(self) -> None:
        self.url = "https://www.nyse.com/api/quotes/filter"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }

    def get_data(self):
        symbols_names = {}
        results_per_page = 1001  # Only 1k is returned

        # Iterate over all pages, until resultPerPage < 1000
        for page_no in range(1, 100):
            post_data = self.gen_post_data(page_no, results_per_page)
            response = requests.post(self.url, headers=self.headers, json=post_data)

            if response.status_code == 200:
                # Parse response to get symbols and names, for this page
                try:
                    all_stocks_data, valid_data = self.parse_response(response)
                except:
                    raise Exception(
                        f":: NYSEListing: Cannot parse {page_no} page response."
                    )
                else:
                    symbols_names.update(valid_data)
                    # Check if last page or pagination remaining
                    if len(all_stocks_data) < 1000:
                        break
            else:
                raise Exception(
                    f":: NYSEListing Error: {response.status_code} {response.text}"
                )

        self.save_to_cache(symbols_names)

        # Return a queue of symbols, to scrape
        symbols = deque(symbols_names.keys())

        logger.debug(f":: NYSEListing: Found {len(symbols)} stocks.")
        return symbols

    def parse_response(self, response):
        all_stocks = response.json()

        valid_stocks = [
            i
            for i in all_stocks
            if i.get("symbolTicker")
            and i.get("instrumentName")
            and i["symbolTicker"] == i.get("normalizedTicker")
            and i["micCode"] == "XNYS"
        ]

        valid_symbol_names = {
            stock["symbolTicker"]: stock["instrumentName"] for stock in valid_stocks
        }
        return all_stocks, valid_symbol_names

    def save_to_cache(self, symbols: Dict[str, str]):
        try:
            cache_listings(symbols)
        except:
            logger.error(":: NYSEListing Error: Cannot save listings to cache.")

    def gen_post_data(self, page_no, results_per_page):
        return {
            "instrumentType": "EQUITY",
            "pageNumber": page_no,
            "sortColumn": "NORMALIZED_TICKER",
            "sortOrder": "ASC",
            "maxResultsPerPage": results_per_page,
            "filterToken": "",
        }
