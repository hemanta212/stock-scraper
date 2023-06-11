"""
A wrapper around requests to handle proxy rotation and retries.
- Proxy and rotation is handled by free-proxy library.
- FreeProxy will test and return only working proxies.
- As Fallback, we do max retries with the proxy before disabling it.
"""


import threading
import time
from queue import Queue
from typing import Callable

import requests
from fp.errors import FreeProxyException
from fp.fp import FreeProxy

from src import logger


class RequestProxy:
    def __init__(
        self,
        use_proxy=False,
        max_retries=5,
        timeout=10.0,
        cancel_func: Callable[[], bool] = lambda: False,
    ):
        self.session = requests.Session()
        self.use_proxy = use_proxy
        self.proxy = (
            self.set_proxy(timeout=timeout, cancel_func=cancel_func)
            if self.use_proxy
            else None
        )
        self.max_retries = max_retries
        self.disabled = False
        # once disabled the request method always returns a 407
        self.disabled_response = DisabledProxyResponse()

    def request(
        self,
        method: str,
        url: str,
        cancel_func: Callable[[], bool] = lambda: False,
        tries=0,
        timeout=10.0,
        **kwargs,
    ):
        if self.disabled:
            return self.disabled_response

        if self.proxy:
            kwargs["proxies"] = {"http": self.proxy, "https": self.proxy}
        else:
            kwargs["proxies"] = None

        try:
            response = self.session.request(method, url, timeout=timeout, **kwargs)
        except Exception as e:
            proxy = "Proxy" if self.proxy else ""
            # Only apply cancellation for proxy requests
            is_cancelled = cancel_func() and self.use_proxy

            if tries == self.max_retries or is_cancelled:
                logger.error(f":: {proxy} Retries Maxed out: Disabling Scraper")
                self.disabled = True
                return self.disabled_response
            else:
                logger.debug(f":: {proxy} Request Error: {self.proxy}, {e} Rotating")
                self.proxy = self.set_proxy(cancel_func) if self.use_proxy else None
                return self.request(
                    method,
                    url,
                    cancel_func=cancel_func,
                    tries=tries + 1,
                    timeout=timeout,
                    **kwargs,
                )

        return response

    def set_proxy(
        self,
        cancel_func: Callable[[], bool] = lambda: False,
        tries: int = 0,
        timeout=10.0,
    ):
        logger.debug(f":: Proxy: Getting new proxy, please wait..")
        try:
            fp = FreeProxy(https=True, anonym=True)
            proxy = with_timeout(timeout, fp.get)
            logger.debug(f":: Proxy Selected: {proxy}")
            return proxy
        except (FreeProxyException, TimeoutError) as e:
            logger.debug(f":: Proxy Error: {e}")
            if tries >= 3 or cancel_func():  # use 3 for no available proxy errors
                self.disabled = True
                return None
            return self.set_proxy(
                cancel_func=cancel_func, tries=tries + 1, timeout=timeout
            )


class DisabledProxyResponse(requests.Response):
    def __init__(self):
        super().__init__()
        self.status_code = 407

    def json(self):
        return {"error": "Proxy Disabled"}


def with_timeout(time_limit, func, *args, **kwargs):
    """
    Run a function with a time limit.
    If the function does not return within the time limit, return None
    """
    q = Queue()

    def wrapper(*args, **kwargs):
        try:
            q.put(func(*args, **kwargs))
        except Exception as e:
            q.put(e)

    t = threading.Thread(target=wrapper, args=args, kwargs=kwargs)
    t.start()
    t.join(time_limit)
    if t.is_alive():
        raise TimeoutError(f":: Proxy Timeout: {time_limit}s")
    else:
        return q.get()
