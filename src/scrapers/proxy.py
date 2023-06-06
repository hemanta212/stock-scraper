import sys
import requests
import loguru
from fp.fp import FreeProxy

import requests


class RequestProxy:
    def __init__(self):
        self.session = requests.Session()
        self.set_proxy()

    def set_proxy(self):
        loguru.logger.debug(f":: Proxy: Getting new proxy, please wait..")
        self.proxy = FreeProxy(https=True).get()
        loguru.logger.debug(f":: Proxy Used: {self.proxy}")

    def request(self, method, url, tries=0, **kwargs):
        if self.proxy:
            kwargs["proxies"] = {"http": self.proxy, "https": self.proxy}
        else:
            kwargs["proxies"] = None

        try:
            response = self.session.request(method, url, **kwargs)
        except Exception as e:
            if tries == 3:
                loguru.logger.error(f":: Proxy Maxed out: Disabling proxy")
                self.proxy = None
                return self.request(method, url, tries=tries + 1, **kwargs)
            else:
                loguru.logger.error(f":: Proxy Error: {self.proxy}, {e} Rotating")
                self.set_proxy()
                return self.request(method, url, tries=tries + 1, **kwargs)

        return response
