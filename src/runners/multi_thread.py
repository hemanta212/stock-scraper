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
from functools import partial
from pprint import pformat
from typing import Callable, Deque, Dict, List, Tuple

from src import logger
from src.runners.utils import (
    cancel_func,
    fix_duplication_and_missed_symbols,
    match_scrapers_failures,
)
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

    failures = fix_duplication_and_missed_symbols(result, symbols)
    logger.debug(f":: Failed symbols {len(failures)}: {pformat(failures)}")

    # Second Pass: Retry failures with alternate scraper, disable cancellation
    if reprocess_failures and failures:
        result = reprocess_failure(instance_func, scrapers, failures, result)

    failures = fix_duplication_and_missed_symbols(result, symbols)
    return list(result.data.values()), failures


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
