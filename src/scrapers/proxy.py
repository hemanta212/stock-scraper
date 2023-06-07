"""
A wrapper around requests to handle proxy rotation and retries.
- Proxy and rotation is handled by free-proxy library.
- FreeProxy will test and return only working proxies.
- As Fallback, we do max retries with the proxy before disabling it.
"""

import sys
import requests
import loguru
from fp.fp import FreeProxy
from fp.errors import FreeProxyException

import requests


class RequestProxy:
    def __init__(self, use_proxy=True, max_retries=5):
        self.session = requests.Session()
        self.proxy = self.set_proxy() if use_proxy else None
        self.max_retries = max_retries
        self.disabled = False
        # once disabled the request method always returns a 407
        self.disabled_response = DisabledProxyResponse()

    def request(self, method, url, tries=0, **kwargs):
        if self.disabled:
            return self.disabled_response

        if self.proxy:
            kwargs["proxies"] = {"http": self.proxy, "https": self.proxy}
        else:
            kwargs["proxies"] = None

        try:
            response = self.session.request(method, url, **kwargs)
        except Exception as e:
            if tries == self.max_retries:
                loguru.logger.error(f":: Proxy Maxed out: Disabling scraper instance")
                self.disabled = True
                return self.disabled_response
            else:
                loguru.logger.error(f":: Proxy Error: {self.proxy}, {e} Rotating")
                self.set_proxy()
                return self.request(method, url, tries=tries + 1, **kwargs)

        return response

    def set_proxy(self, tries=0):
        loguru.logger.debug(f":: Proxy: Getting new proxy, please wait..")
        try:
            proxy = FreeProxy(https=True, anonym=True).get()
            loguru.logger.debug(f":: Proxy Selected: {proxy}")
            return proxy
        except FreeProxyException as e:
            loguru.logger.error(f":: Proxy Error: {e}")
            if tries == 3:  # use 3 for no available proxy errors
                self.disabled = True
                return None
            return self.set_proxy(tries=tries + 1)


class DisabledProxyResponse(requests.Response):
    def __init__(self):
        super().__init__()
        self.status_code = 407

    def json(self):
        return {"error": "Proxy Disabled"}
