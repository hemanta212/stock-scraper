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

import lxml.html
import pytz
import requests

from src import logger
from src.databases import ListingCache
from src.utils.proxy import RequestProxy


class StockAnalysisAPI:
    def __init__(self, use_proxy=False, rate_limit=0):
        self.BASE_URL = "https://stockanalysis.com/api/quotes/s/{}"
        self.use_proxy = use_proxy
        self.rate_limit = rate_limit

    def setup(self):
        self.working = True
        self.session = RequestProxy(use_proxy=self.use_proxy)
        if not self.test_connection():
            self.session = RequestProxy(use_proxy=self.use_proxy)
            if not self.test_connection():
                logger.error(":: Setting Scraper as Dead")
                self.working = False

    def get_data(self, symbol, cancel_func=lambda: False):
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
            logger.error(
                f":: StockAnalysisAPI failed {symbol}: {response.status_code} {e}"
            )
            return None

        if response.status_code == 200:
            return self.convert_data(data.get("data"), symbol)
        elif response.status_code == 407 or self.session.disabled:
            logger.error(f":: YahooApi Proxy Failure, making scraper dead")
            self.working = False
        else:
            logger.error(f":: StockAnalysisAPI failed {symbol}: {response.status_code}")
            return None

    def convert_data(self, stock_data, symbol):
        if not stock_data:
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
            value = stock_data.get(old_key)
            if not value:
                logger.error(
                    f":: StockAnalysisAPI: {symbol} Failed to get {new_key}:{old_key}"
                )
                logger.debug(pformat(stock_data))
                return None
            new_data[new_key] = value

        name = self.get_name(symbol)
        date = self.parse_date(stock_data.get("u"))
        if not name or not date:
            return None

        new_data["name"], new_data["symbol"], new_data["timestamp"] = name, symbol, date
        return new_data

    def test_connection(self):
        logger.info(":: Testing connection to StockAnalysis API")

        try:
            data = self.get_data("NKE")
        except Exception as e:
            logger.error(e)
            data = None

        if data:
            logger.info(":: Connection to StockAnalysis API successful")
            return True
        else:
            logger.error(":: Connection to StockAnalysis API failed")
            return False

    def get_headers(self):
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

    def get_name(self, symbol):
        """Get name from listing cache database, if not found, scrape it"""
        try:
            db = ListingCache()
            name = db.get_name(symbol)[0]
        except Exception as e:
            name = None

        if not name:
            name = self.scrape_name(symbol)
        return name

    def scrape_name(self, symbol):
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
            logger.error(f":: StockAnalysisAPI getting name failed: {e} {title}")
            return None

    def parse_date(self, raw_date):
        if not raw_date:
            logger.error(":: StockAnalysisAPI parse_date failed: No date")
            return None

        # convert 'Jun 6, 2023, 4:00 PM', or 'Jun 6, 2023, 4:00 AM EDT' etc to timestamp
        # Use regular expressions to extract the date and time
        pattern = r"([A-Za-z]{3} \d{1,2}, \d{4}, \d{1,2}:\d{2} [APM]{2})"
        matches = re.findall(pattern, raw_date)
        if matches:
            # Extract the first match
            raw_date = matches[0]
        else:
            logger.error(f":: StockAnalysisAPI parse_date failed: regex {raw_date}")
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
