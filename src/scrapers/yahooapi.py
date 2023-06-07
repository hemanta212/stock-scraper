"""
Yahoo API
- Loading the yahoo website, cookies are generated and stored in the browser.
- Same cookies are transmited over to the endpoint during request
- However, another element, crumb is sent along with the request
- This crumb is generated from the cookie and another endpoint.
- Once, crumb and cookie is available the request can be made.

NOTE: The cookie surprisingly does not expire, so it can be stored and reused
This means, we dont have to spin up a playwright instance as often.
"""
import json
import os
import sys
import urllib.parse
from datetime import datetime, timedelta
from pprint import pprint

import pytz

from src import logger
from src.utils.cookie_getter import get_browser_cookie
from src.utils.proxy import RequestProxy


class YahooAPI:
    def __init__(self, use_proxy=False):
        self.BASE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
        self.working = True
        self.session = RequestProxy(use_proxy=use_proxy)
        self.cookie_file_path = "cookie.json"
        self.cookie_cred = self.load_default_cookie()
        # refresh default cookie if not working
        if not self.test_connection():
            self.cookie_cred = self.regenerate_cookie()
            # if still not working, then set works to False
            if not self.test_connection():
                logger.error(":: Setting Yahoo API as Dead")
                self.working = False

    def get_data(self, symbol):
        # normalize symbol eg BRK.B -> BRK-B
        symbol = symbol.replace(".", "-")

        url, headers = self.build_request(symbol)
        response = self.session.request("get", url, headers=headers)
        api_error = None

        if response.status_code == 200:
            data = response.json()
            api_error = data["quoteResponse"]["error"]
            result_data = data["quoteResponse"]["result"]
            if api_error is None and result_data:
                return self.convert_data(result_data[0], symbol)

        logger.error(
            f":: YahooApi Failed {symbol}: {response.status_code} {response.text} {api_error}"
        )
        return None

    def convert_data(self, stock_data, symbol):
        # favor longer name and fallback to shorter name
        stock_data["name"] = stock_data.get("longName") or stock_data.get("shortName")

        conversion_map = {
            "name": "name",
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
            value = stock_data.get(old_key)
            if not value:
                logger.error(f":: YahooApi {symbol}: Failed to get {old_key}")
                print(stock_data)
                return None

            # for values with multi forms, prefer the raw form
            if isinstance(value, dict):
                value = value.get("raw")
            new_data[new_key] = value

        # Add remaining data
        new_data["symbol"] = symbol
        new_data["timestamp"] = self.parse_date(stock_data)
        return new_data

    def test_connection(self):
        logger.info(":: Testing connection to Yahoo API")

        try:
            data = self.get_data("NKE")
        except Exception as e:
            logger.error(e)
            data = None

        if data:
            logger.info(":: Connection to Yahoo API successful")
            return True
        else:
            logger.error(":: Connection to Yahoo API failed")
            return False

    def build_request(self, symbol):
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
            "symbols": symbol,
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
            "Referer": f"https://finance.yahoo.com/quote/{symbol}",
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

    def regenerate_cookie(self):
        logger.info(":: Yahoo API: Regenerating cookie")
        cookies = get_browser_cookie("https://finance.yahoo.com/quote/NKE")

        if not cookies:
            logger.error(":: Yahoo API: PlayWright Failed to get cookie")
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
            logger.error(":: Yahoo API: Failed to get crumb")
            return {"cookie": {}, "crumb": ""}

        cookie_data = {"cookie": cookie, "crumb": crumb}
        logger.info(f":: Yahoo API: Generated new cookie {cookie_str}")

        with open(self.cookie_file_path, "w") as f:
            json.dump(cookie_data, f)

        return cookie_data

    def get_crumb(self, cookie):
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

    def load_default_cookie(self):
        if not os.path.exists(self.cookie_file_path):
            return self.regenerate_cookie()
        with open(self.cookie_file_path) as rf:
            return json.load(rf)

    def parse_date(self, data):
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
