import os
import sys
import json
import urllib.parse
from pprint import pprint
from datetime import datetime

import loguru

from src.scrapers.cookie_getter import get_browser_cookie
from src.scrapers.proxy import RequestProxy


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
                loguru.logger.error(":: Setting Yahoo API as Dead")
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
                return self.convert_data(result_data[0])

        loguru.logger.error(
            f":: YahooApi:Failed {response.status_code} {response.text} {api_error}"
        )
        return None

    def convert_data(self, stock_data):
        # favor longer name and fallback to shorter name
        stock_data["name"] = stock_data.get("longName") or stock_data.get("shortName")

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
            value = stock_data.get(old_key)
            if not value:
                loguru.logger.error(f":: YahooApi: Failed to get {old_key}")
                print(stock_data)
                return None

            # for values with multi forms, prefer the raw form
            if isinstance(value, dict):
                value = value.get("raw")
            new_data[new_key] = value

        # Add remaining data
        new_data["timestamp"] = int(datetime.utcnow().timestamp())
        return new_data

    def test_connection(self, tries=0):
        loguru.logger.info(":: Testing connection to Yahoo API")
        url, headers = self.build_request("NKE")

        try:
            response = self.session.request("get", url, headers=headers)
        except Exception as e:
            loguru.logger.error(f":: Unknown Error: {e}")
            return False

        if (
            response.status_code == 200
            and response.json()["quoteResponse"]["error"] is None
        ):
            loguru.logger.info(":: Connection to Yahoo API successful")
            return True
        else:
            loguru.logger.error(":: Connection to Yahoo API failed")
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
        loguru.logger.info(":: Yahoo API: Regenerating cookie")
        cookies = get_browser_cookie("https://finance.yahoo.com/quote/NKE")

        if not cookies:
            loguru.logger.error(":: Yahoo API: PlayWright Failed to get cookie")
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
            loguru.logger.error(":: Yahoo API: Failed to get crumb")
            return {"cookie": {}, "crumb": ""}

        cookie_data = {"cookie": cookie, "crumb": crumb}
        loguru.logger.info(f":: Yahoo API: Generated new cookie {cookie_str}")

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
