from collections import deque
from typing import Dict

import requests
from bs4 import BeautifulSoup

from src import logger
from src.databases import cache_listings


class Listing:
    url = "https://www.slickcharts.com/nasdaq100"

    def get_data(self):
        headers = self.get_headers()
        response = requests.get(self.url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        table = soup.find(
            "table", {"class": "table table-hover table-borderless table-sm"}
        )
        tr_blocks = table.find_all("tr")

        symbols_names = {}
        for block in tr_blocks:
            td_blocks = block.find_all("td")
            if len(td_blocks) == 0:
                continue
            full_name = td_blocks[1].text.strip()
            symbol = td_blocks[2].text.strip()
            symbols_names[symbol] = full_name

        self.save_to_cache(symbols_names)
        symbols = deque(symbols_names.keys())

        logger.debug(
            f":: {self.__class__.__name__}: Found {len(symbols_names)} stocks."
        )
        return symbols

    def save_to_cache(self, symbols: Dict[str, str]):
        try:
            cache_listings(symbols)
        except:
            logger.error(
                f":: {self._class__.__name__} Error: Cannot save listings to cache."
            )

    def get_headers(self):
        headers = {
            "authority": "www.slickcharts.com",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.5",
            "cache-control": "max-age=0",
            "cookie": "arp_scroll_position=0",
            "referer": "https://www.google.com/",
            "sec-ch-ua": '"Not.A/Brand";v="8", "Chromium";v="114", "Brave";v="114"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "cross-site",
            "sec-fetch-user": "?1",
            "sec-gpc": "1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        }
        return headers


class SandP500(Listing):
    def __init__(self):
        self.url = "https://www.slickcharts.com/sp500"


class Nasdaq100(Listing):
    def __init__(self):
        self.url = "https://www.slickcharts.com/nasdaq100"


class DowJones30(Listing):
    def __init__(self):
        self.url = "https://www.slickcharts.com/dowjones"
