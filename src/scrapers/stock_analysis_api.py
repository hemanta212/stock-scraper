"""
StockAnalysis.com API
- The api returns json response with single char obuscated keys.
- API doesnot require any cookies or auth.
- However, it is little slower and needs rate limiting.
- Response doesnot contain the full name of stock.
- We primarily use listings cache, then fallback to just scraping the name from website.
"""

import re
import time
from datetime import datetime
from pprint import pformat
from typing import Callable, Dict, List, Optional, Tuple

import lxml.html
import pytz
import requests

from src import logger
from src.databases import ListingCache
from src.types import StockInfo
from src.utils.proxy import RequestProxy


class StockAnalysisAPI:
    def __init__(self, batch_size=1, use_proxy=False, rate_limit=0.0) -> None:
        self.BASE_URL = "https://stockanalysis.com/api/quotes/s/{}"
        self.batch_size = batch_size
        self.use_proxy = use_proxy
        self.rate_limit = rate_limit

    def setup(self, cancel_func: Callable[[], bool] = lambda: False) -> None:
        """
        Setup the scraper, create proxy session, test connection
        """
        self.working = True
        self.session = RequestProxy(use_proxy=self.use_proxy, cancel_func=cancel_func)
        if not self.test_connection(cancel_func=cancel_func):
            # Retry a new proxy once
            self.session = RequestProxy(
                use_proxy=self.use_proxy, cancel_func=cancel_func
            )
            if not self.test_connection(cancel_func=cancel_func):
                # if still not working
                logger.error(":: Setting Scraper as Dead")
                self.working = False

    def get_data(
        self, symbols: List[str], cancel_func: Callable[[], bool] = lambda: False
    ) -> List[Optional[StockInfo]]:
        """
        This API doesnot support batch requests.
        This method is wrapper for interface consistency.
        """
        data = self._get_data(symbols[0], cancel_func=cancel_func)
        return [data]

    def _get_data(
        self, symbol: str, cancel_func: Callable[[], bool] = lambda: False
    ) -> Optional[StockInfo]:
        """
        Builds a url, header pair and makes a request.
        if successful, converts the data to our uniform format.
        """
        if self.rate_limit:
            time.sleep(self.rate_limit)

        url, headers = self.BASE_URL.format(symbol), self.get_headers()
        response = self.session.request(
            "get", url, headers=headers, cancel_func=cancel_func
        )

        data = None
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError as e:
            logger.warning(f":: {self} failed {symbol}: {response.status_code} {e}")
            return None

        if response.status_code == 200:
            return self.convert_data(data.get("data"), symbol)
        elif response.status_code == 407 or self.session.disabled:
            # This is our own response for proxy failure.
            logger.error(f":: {self} Failure with proxy, making scraper dead")
            self.working = False

        logger.warning(f":: {self} failed {symbol}: {response.status_code}")
        return None

    def convert_data(self, stock_info: dict, symbol: str) -> Optional[StockInfo]:
        """
        Converts the api specific format and namings to our uniform format.
        """
        if not stock_info:
            return None

        new_data = {}
        # info we need
        conversion_map = {
            "p": "price",
            "v": "volume",
            "mc": "marketcap",
            "h": "highprice",
            "l": "lowprice",
            "o": "open",
            "cl": "prevclose",
        }
        for old_key, new_key in conversion_map.items():
            value = stock_info.get(old_key)

            if not value:
                logger.warning(f":: {self}: {symbol} Failed to get {new_key}:{old_key}")
                logger.debug(pformat(stock_info))
                return None

            new_data[new_key] = value

        name = self.get_name(symbol)
        date = self.parse_date(stock_info.get("u"))
        if not name or not date:
            return None

        new_data["name"], new_data["symbol"], new_data["timestamp"] = name, symbol, date
        return StockInfo(**new_data)

    def test_connection(self, cancel_func: Callable[[], bool]) -> bool:
        logger.info(f":: Testing connection to {self}")

        try:
            data = self.get_data(["NKE"], cancel_func=cancel_func)
        except Exception as e:
            logger.exception(e)
            data = None

        if data:
            logger.info(f":: Connection to {self} successful")
            return True
        else:
            logger.error(f":: Connection to {self} failed")
            return False

    def get_headers(self) -> dict:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Alt-Used": "stockanalysis.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }
        return headers

    def get_name(self, symbol: str) -> Optional[str]:
        "Get name from listing cache database, if not found, scrape it"
        try:
            db = ListingCache()
            name = db.get_name(symbol)[0]
        except Exception as e:
            name = None

        if not name:
            name = self.scrape_name(symbol)
        return name

    def scrape_name(self, symbol: str) -> Optional[str]:
        time.sleep(1)
        url = f"https://stockanalysis.com/stocks/{symbol}/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Alt-Used": "stockanalysis.com",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }
        response, title = None, None
        try:
            response = self.session.request("get", url, headers=headers)
            tree = lxml.html.fromstring(response.content)
            title = tree.xpath('//*[@id="main"]/div[1]/div[1]/div[1]/h1')
            name = title[0].text_content().split("(")[0].strip()
            return name
        except Exception as e:
            logger.exception(f":: {self} getting name failed: {e} {title}")
            return None

    def parse_date(self, raw_date: str) -> Optional[int]:
        if not raw_date:
            logger.error(f":: {self} parse_date failed: No date")
            return None

        # convert 'Jun 6, 2023, 4:00 PM', or 'Jun 6, 2023, 4:00 AM EDT' etc to timestamp
        # Use regular expressions to extract the date and time
        pattern = r"([A-Za-z]{3} \d{1,2}, \d{4}, \d{1,2}:\d{2} [APM]{2})"
        matches = re.findall(pattern, raw_date)
        if matches:
            # Extract the first match
            raw_date = matches[0]
        else:
            logger.error(f":: {self} parse_date failed: regex {raw_date}")
            return None

        # Parse the market time string
        date = datetime.strptime(raw_date, "%b %d, %Y, %I:%M %p")
        exchange_timezone = pytz.timezone("America/New_York")
        # set the parsed date's timezone
        date = exchange_timezone.localize(date)

        # Create a UTC timezone
        utc_timezone = pytz.timezone("UTC")
        utc_timestamp = int(date.astimezone(utc_timezone).timestamp())

        return utc_timestamp

    def __repr__(self):
        return self.__class__.__name__

    def __str__(self):
        return (
            f"{self.__class__.__name__} {'(PROXY)' if self.use_proxy else ''}".strip()
        )
