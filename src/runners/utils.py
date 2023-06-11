from collections import deque
from typing import Callable, Deque, Dict, List

from src import logger
from src.scrapers import ScraperType
from src.types import Result


def cancel_func(symbol_func: Callable[[], str]):
    # check if the symbol_func that fetches next symbol itself is empty
    # Cancellation is only used for proxy scrapers
    # To stop the time waste searching and rotating free proxies when queue is already empty
    return len(symbol_func.__self__) == 0


def fix_duplication_and_missed_symbols(
    result: Result, symbols: Deque[str]
) -> Dict[str, str]:
    failures, data = result.failures, result.data
    # Get real failures, some failure arises due to same symbol being taken up by multiple scrapers
    failures = {sym: s for sym, s in failures.items() if sym not in data}

    # Add missed symbols to failures,
    missed_symbols = [sym for sym in symbols if sym not in data and sym not in failures]
    # and assign it as "missed"
    failures.update({sym: "missed" for sym in missed_symbols})
    return failures


def match_scrapers_failures(
    scrapers: List[ScraperType], failures: Dict[str, str]
) -> Dict[ScraperType, Callable[[], str]]:
    """
    When a stock fetch fails, its symbol and scraper used gets documented
    Here we try to read it, and assign symbol to different scraper
    """
    new_scraper_symbols_match: Dict[ScraperType, Callable[[], str]] = {}
    # reverse failures dict, from {sym: scraper} to {scraper: [sym1, sym2]}
    rev_failures = {scraper_name: deque() for scraper_name in set(failures.values())}
    for symbol, scraper_name in failures.items():
        rev_failures[scraper_name].append(symbol)

    for scraper_name, symbol in rev_failures.items():
        available_scrapers = [
            scraper for scraper in scrapers if repr(scraper) != scraper_name
        ]
        available_non_proxy_scrapers = [
            scraper for scraper in available_scrapers if not scraper.use_proxy
        ]
        if available_non_proxy_scrapers:
            new_scraper_symbols_match[available_non_proxy_scrapers[0]] = symbol.pop
        elif available_scrapers:
            new_scraper_symbols_match[available_scrapers[0]] = symbol.pop
        else:
            logger.debug(":: No alternate scrapers available to reprocess failures.")
            new_scraper_symbols_match[scrapers[0]] = symbol.pop

    return new_scraper_symbols_match
