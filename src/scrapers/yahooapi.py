"""
Yahoo API
- Loading the yahoo website, cookies are generated and stored in the browser.
- Same cookies are transmited over to the endpoint during request
- However, another element, crumb is sent along with the request
- This crumb is generated from the cookie and another endpoint.
- Once, crumb and cookie is available the request can be made.

NOTE: The cookie surprisingly does not expire(till 1 yr), so it can be stored and reused
This means, we dont have to spin up a playwright instance as often.
"""
import json
import os
import time
import urllib.parse
from datetime import datetime
from pprint import pformat
from typing import Callable, Dict, List, Optional, Tuple

import pytz

from src import logger
from src.types import StockInfo
from src.utils.cookie_getter import get_browser_cookie
from src.utils.proxy import RequestProxy
from src.utils.validator import is_valid_stock


class YahooAPI:
    def __init__(self, batch_size=10, use_proxy=False, rate_limit=0.0) -> None:
        self.BASE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
        self.batch_size = batch_size
        self.use_proxy = use_proxy
        self.rate_limit = rate_limit
        self.cookie_file_path = "cookie.json"

    def setup(self, cancel_func: Callable[[], bool] = lambda: False) -> None:
        self.working = True
        self.session = RequestProxy(use_proxy=self.use_proxy, cancel_func=cancel_func)
        self.cookie_cred = self.load_default_cookie()
        # refresh default cookie if not working
        if not self.test_connection(cancel_func=cancel_func):
            self.cookie_cred = self.regenerate_cookie()
            # if still not working, then set works to False
            if not self.test_connection(cancel_func=cancel_func):
                logger.error(f":: Setting {self} as Dead")
                self.working = False

    def get_data(
        self, symbols: List[str], cancel_func: Callable[[], bool] = lambda: False
    ) -> List[Optional[StockInfo]]:
        """
        Receives and Tries multiple symbols at once
        For those symbols that failed, tries one by one
        Then returns all data
        """
        data = self._get_data(symbols, cancel_func=cancel_func)
        result: List[Optional[StockInfo]] = []

        failures = []
        for stock_data, symbol in zip(data, symbols):
            if stock_data and is_valid_stock(stock_data):
                result.append(stock_data)
            else:
                failures.append(symbol)

        if not failures:
            return result

        # first pass try all failures at once
        failures_data = self._get_data(failures, cancel_func=cancel_func)

        # second pass try one by one if still failed
        for stock_data, symbol in zip(failures_data, failures):
            if stock_data and is_valid_stock(stock_data):
                result.append(stock_data)
            else:
                # try individually again, then append anyway
                stock_data = self._get_data([symbol], cancel_func=cancel_func)[0]
                result.append(stock_data)

        return result

    def _get_data(
        self, symbols: List[str], cancel_func: Callable[[], bool] = lambda: False
    ) -> List[Optional[StockInfo]]:
        """
        Builds a url, header pair and makes a request.
        if successful, converts the data to our uniform format.
        """
        if self.rate_limit:
            time.sleep(self.rate_limit)

        # normalize symbol eg BRK.B -> BRK-B
        symbols = [symbol.replace(".", "-") for symbol in symbols]

        url, headers = self.build_request(symbols)
        response = self.session.request(
            "get", url, headers=headers, cancel_func=cancel_func
        )
        api_error = None

        if response.status_code == 200:
            data = response.json()
            api_error = data["quoteResponse"]["error"]
            result_data = data["quoteResponse"]["result"]
            if api_error is None and result_data:
                converted_data = [
                    self.convert_data(stock_info, symbol)
                    for stock_info, symbol in zip(result_data, symbols)
                ]
                return converted_data

        if response.status_code == 407 or self.session.disabled:
            # This is our own response code for proxy failure.
            logger.error(f":: {self} Failure with proxy, making scraper dead")
            self.working = False
        else:
            logger.warning(
                f":: {self} Failed {symbols}: {response.status_code} {response.text} {api_error}"
            )

        failed_data: List[Optional[StockInfo]] = [None] * len(symbols)
        return failed_data

    def convert_data(self, stock_info: dict, symbol: str) -> Optional[StockInfo]:
        # favor longer name and fallback to shorter name or displayName
        stock_info["name"] = (
            stock_info.get("longName")
            or stock_info.get("shortName")
            or stock_info.get("displayName")
        )

        conversion_map = {
            "name": "name",
            "symbol": "symbol",
            "marketCap": "marketcap",
            "regularMarketPrice": "price",
            "regularMarketVolume": "volume",
            "regularMarketDayHigh": "highprice",
            "regularMarketDayLow": "lowprice",
            "regularMarketOpen": "open",
            "regularMarketPreviousClose": "prevclose",
        }

        new_data = {}
        for old_key, new_key in conversion_map.items():
            value = stock_info.get(old_key)
            if not value:
                # if any one value is missing, then skip this stock
                logger.warning(f":: {self} {symbol}: Failed to get {old_key}")
                logger.debug(pformat(stock_info))
                break
            # for values with multi forms, prefer the raw form
            if isinstance(value, dict):
                value = value.get("raw")
            new_data[new_key] = value
        else:
            # Derive timestamp
            new_data["timestamp"] = self.parse_date(stock_info)
            return StockInfo(**new_data)

        return None

    def test_connection(self, cancel_func: Callable[[], bool]) -> bool:
        logger.info(f":: Testing connection to {self}")

        data = None
        try:
            data = self.get_data(["NKE"], cancel_func=cancel_func)
        except Exception as e:
            logger.exception(e)

        if data:
            logger.info(f":: Connection to {self} successful")
            return True
        else:
            logger.error(f":: Connection to {self} failed")
            return False

    def build_request(self, symbols: List[str]) -> Tuple[str, Dict[str, str]]:
        crumb, cookie_data = self.cookie_cred["crumb"], self.cookie_cred["cookie"]
        cookie = "; ".join([f"{k}={v}" for k, v in cookie_data.items()]).strip()
        fields = [
            "longName",
            "shortName",
            "symbol",
            "marketCap",
            "regularMarketPrice",
            "regularMarketVolume",
            "regularMarketDayHigh",
            "regularMarketDayLow",
            "regularMarketOpen",
            "regularMarketPreviousClose",
            "gmtOffSetMilliseconds",
            "exchangeTimezoneName",
            "regularMarketTime",
        ]
        query_params = {
            "symbols": ",".join(symbols),
            "formatted": "true",
            "crumb": crumb,
            "lang": "en-US",
            "region": "US",
            "corsDomain": "finance.yahoo.com",
            "fields": ",".join(fields),
        }
        headers = {
            "Host": "query1.finance.yahoo.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://finance.yahoo.com",
            "Origin": "https://finance.yahoo.com",
            "DNT": "1",
            "Connection": "keep-alive",
            "Cookie": cookie,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "TE": "trailers",
        }
        url = self.BASE_URL + "?" + urllib.parse.urlencode(query_params)
        return url, headers

    def regenerate_cookie(self) -> Dict:
        logger.info(f":: {self}: Regenerating cookie")
        cookies = get_browser_cookie("https://finance.yahoo.com/quote/NKE")

        if not cookies:
            logger.error(f":: {self}: PlayWright Failed to get cookie")
            return {"cookie": {}, "crumb": ""}

        domains = [".yahoo.com", ".finance.yahoo.com"]
        cookie_names = ["A1", "A3", "cmp", "PRF", "A1S"]
        valid_cookies = [
            c
            for c in cookies
            if c.get("domain") in domains and c.get("name") in cookie_names
        ]

        cookie = {c.get("name"): c.get("value") for c in valid_cookies}
        cookie_str = "; ".join([f"{k}={v}" for k, v in cookie.items()]).strip()
        crumb = self.get_crumb(cookie_str)
        if not crumb:
            logger.error(f":: {self}: Failed to get crumb")
            return {"cookie": {}, "crumb": ""}

        cookie_data = {"cookie": cookie, "crumb": crumb}
        logger.info(f":: {self}: Generated new cookie {cookie_str}")

        with open(self.cookie_file_path, "w") as f:
            json.dump(cookie_data, f)

        return cookie_data

    def get_crumb(self, cookie: str) -> Optional[str]:
        url = "https://query1.finance.yahoo.com/v1/test/getcrumb"
        headers = {
            "Host": "query1.finance.yahoo.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0",
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.5",
            "content-type": "text/plain",
            "sec-ch-ua": '"Not.A/Brand";v="8", "Chromium";v="114", "Brave";v="114"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "sec-gpc": "1",
            "cookie": cookie,
            "Referer": "https://finance.yahoo.com/",
            "Referrer-Policy": "no-referrer-when-downgrade",
        }
        response = self.session.request("get", url, headers=headers)
        if response.status_code == 200:
            return response.text
        else:
            return None

    def load_default_cookie(self) -> dict:
        if not os.path.exists(self.cookie_file_path):
            return self.regenerate_cookie()
        with open(self.cookie_file_path) as rf:
            return json.load(rf)

    def parse_date(self, data) -> int:
        exchange_timezone_name = data["exchangeTimezoneName"]
        regular_market_time_raw = data["regularMarketTime"]["raw"]

        exchange_timezone = pytz.timezone(exchange_timezone_name)
        # Convert regular_market_time_raw to datetime
        regular_market_time = datetime.fromtimestamp(regular_market_time_raw)
        # Convert regular market time to the specified time zone
        regular_market_time = regular_market_time.astimezone(exchange_timezone)

        # Create a UTC timezone
        utc_timezone = pytz.timezone("UTC")
        utc_timestamp = int(regular_market_time.astimezone(utc_timezone).timestamp())

        return utc_timestamp

    def __repr__(self):
        return self.__class__.__name__

    def __str__(self):
        return (
            f"{self.__class__.__name__} {'(PROXY)' if self.use_proxy else ''}".strip()
        )
