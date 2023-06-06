import os
import json
import urllib.parse
from pprint import pprint
from datetime import datetime

import requests
import loguru

from .cookie_getter import get_browser_cookie


class YahooAPI:
    def __init__(self):
        self.BASE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
        self.cookie_cred = self.load_default_cookie()
        self.working = True
        # refresh default cookie if not working
        if not self.test_connection():
            self.cookie_cred = self.regenerate_cookie()
            # if still not working, then set works to False
            if not self.test_connection():
                loguru.logger.error(":: Setting Yahoo API as Dead")
                self.working = False

    def get_data(self, symbol):
        url, headers = self.build_request(symbol)
        response = requests.get(url, headers=headers)
        data = response.json()
        api_error = data["quoteResponse"]["error"]
        if response.status_code == 200 and api_error is None:
            return self.convert_data(response.json())
        else:
            loguru.logger.error(
                f":: YahooApi:Failed {response.status_code} {response.text} {api_error}"
            )
            return None

    def convert_data(self, data):
        stock_data = data["quoteResponse"]["result"][0]
        conversion_map = {
            "longName": "name",
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
            value = stock_data[old_key]
            # for values with multi forms, prefer the raw form
            if isinstance(value, dict):
                value = value.get("raw")
            new_data[new_key] = value
        new_data["timestamp"] = int(datetime.utcnow().timestamp())
        return new_data

    def test_connection(self):
        loguru.logger.info(":: Testing connection to Yahoo API")
        url, headers = self.build_request("NKE")
        response = requests.get(url, headers=headers)
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
        cookies = get_browser_cookie("https://finance.yahoo.com/quote/NKE")
        domains = [".yahoo.com", ".finance.yahoo.com"]
        cookie_names = ["A1", "A3", "cmp", "PRF", "A1S"]
        valid_cookies = [
            c
            for c in cookies
            if c.get("domain") in domains and c.get("name") in cookie_names
        ]
        cookie = {c.get("name"): c.get("value") for c in valid_cookies}
        cookie_str = "; ".join([f"{k}={v}" for k, v in cookie.items()]).strip()
        loguru.logger.info(f":: Yahoo API: New cookie {cookie_str}")

        crumb = self.get_crumb(cookie_str)
        cookie_data = {"cookie": cookie, "crumb": crumb}

        cookieFilePath = "cookie.json"
        with open(cookieFilePath, "w") as f:
            json.dump(cookie_data, f)

        return {"cookie": cookie, "crumb": crumb}

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
        response = requests.get(url, headers=headers)
        loguru.logger.info(f":: YahooApi: New Crumb {response.text}")
        return response.text

    def load_default_cookie(self):
        cookieFilePath = "cookie.json"
        if not os.path.exists(cookieFilePath):
            return self.regenerate_cookie()
        with open(cookieFilePath, "r") as rf:
            return json.load(rf)
