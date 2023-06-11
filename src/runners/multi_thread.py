"""
We create and execute multiple tasks, out of same function instance using threadpool.
- First take symbol list and scrapers classes
- The symbol list is deque and one such deque can be shared by 2 scraper
- Create instance func passing scraper classes along with its own deque pop operation
- Then the first pass is ran, tasks are created then waited to complete
- All Scrapers update the global all_data and failures list and dict respectively

- Second Pass: Failure dict is taken and again passed to scrapers
- Failure dict contains the symbol and scraper that failed to extract it
- We then pair symbols and scraper so that symbol get new scraper than previous one.
- After the second pass is completed, we have final failure list

- All data and final failure list are then returned
"""

import concurrent.futures
from collections import deque
from functools import partial
from pprint import pformat
from typing import Callable, Deque, Dict, List, Tuple

from src import logger
from src.runners.single_thread import cancel_func
from src.scrapers import ScraperType
from src.types import Result, StockInfo


def parallel_executor(
    instance_func: Callable[..., None],
    scrapers: List[ScraperType],
    symbol_funcs: List[Callable[[], str]],
    symbols: Deque[str],
    reprocess_failures=True,
) -> Tuple[List[StockInfo], Dict[str, str]]:
    result = Result(data={}, failures={})

    cancel_funcs = [partial(cancel_func, symbol_func) for symbol_func in symbol_funcs]

    # Initial Pass
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(instance_func, scraper, symbol_func, result, cancel_func)
            for scraper, symbol_func, cancel_func in zip(
                scrapers, symbol_funcs, cancel_funcs
            )
        ]
        for future in concurrent.futures.as_completed(futures):
            future.result()

    # Get real failures, some failure arises due to same symbol being taken up by multiple scrapers
    failures, data = result.failures, result.data
    failures = {sym: s for sym, s in failures.items() if sym not in data}
    logger.debug(f":: Failed symbols {len(failures)}: {pformat(failures)}")

    # Second Pass: Retry failures with alternate scraper, disable cancellation
    if reprocess_failures and failures:
        result = reprocess_failure(instance_func, scrapers, failures, result)

    data, failures = result.data, result.failures
    # remove duplicates in all data and failures
    failures = {sym: s for sym, s in failures.items() if sym not in data}

    return list(data.values()), failures


def reprocess_failure(
    instance_func: Callable[..., None],
    scrapers: List[ScraperType],
    failures: Dict[str, str],
    result: Result,
) -> Result:
    result = Result(data=result.data, failures={})
    disabled_cancel_func = lambda: False
    logger.info(":: Reprocessing failures with alternate scraper")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        scrapers_symbols = match_scrapers_failures(scrapers, failures)
        futures = [
            executor.submit(
                instance_func, scraper, symbol_func, result, disabled_cancel_func
            )
            for scraper, symbol_func in scrapers_symbols.items()
        ]
        for future in concurrent.futures.as_completed(futures):
            future.result()
    return result


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
