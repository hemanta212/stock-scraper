"""
A wrapper around requests to handle proxy rotation and retries.
- Proxy and rotation is handled by free-proxy library.
- FreeProxy will test and return only working proxies.
- As Fallback, we do max retries with the proxy before disabling it.
"""


import requests
from fp.errors import FreeProxyException
from fp.fp import FreeProxy

from src import logger


class RequestProxy:
    def __init__(self, use_proxy=True, max_retries=5):
        self.session = requests.Session()
        self.proxy = self.set_proxy() if use_proxy else None
        self.max_retries = max_retries
        self.disabled = False
        # once disabled the request method always returns a 407
        self.disabled_response = DisabledProxyResponse()

    def request(
        self, method, url, cancel_func=lambda: False, tries=0, timeout=5, **kwargs
    ):
        if self.disabled:
            return self.disabled_response

        if cancel_func():
            logger.error(f":: Cancellation signal received.")
            self.disabled = True
            return self.disabled_response

        if self.proxy:
            kwargs["proxies"] = {"http": self.proxy, "https": self.proxy}
        else:
            kwargs["proxies"] = None

        try:
            response = self.session.request(method, url, timeout=timeout, **kwargs)
        except Exception as e:
            if tries == self.max_retries:
                logger.error(f":: Proxy Maxed out: Disabling scraper instance")
                self.disabled = True
                return self.disabled_response
            else:
                logger.error(f":: Proxy Error: {self.proxy}, {e} Rotating")
                self.proxy = self.set_proxy(cancel_func)
                return self.request(
                    method, url, tries=tries + 1, timeout=timeout, **kwargs
                )

        return response

    def set_proxy(self, cancel_func=lambda: False, tries=0):
        logger.debug(f":: Proxy: Getting new proxy, please wait..")
        try:
            proxy = FreeProxy(https=True, anonym=True).get()
            logger.debug(f":: Proxy Selected: {proxy}")
            return proxy
        except FreeProxyException as e:
            logger.error(f":: Proxy Error: {e}")
            if tries == 2 or cancel_func():  # use 2 for no available proxy errors
                self.disabled = True
                return None
            return self.set_proxy(cancel_func=cancel_func, tries=tries + 1)


class DisabledProxyResponse(requests.Response):
    def __init__(self):
        super().__init__()
        self.status_code = 407

    def json(self):
        return {"error": "Proxy Disabled"}
