"""
We create and execute instance function.
- First take symbol list and the scraper to run
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
from collections import deque
from functools import partial
from pprint import pformat
from typing import Callable, Deque, Dict, List, Tuple

from src import logger
from src.scrapers import ScraperType
from src.types import Result, StockInfo


def executor(
    instance_func: Callable[..., None],
    scrapers: List[ScraperType],
    symbol_funcs: List[Callable[[], str]],
    symbols: Deque[str],
    reprocess_failures=True,
) -> Tuple[List[StockInfo], Dict[str, str]]:
    result = Result(data={}, failures={})

    # First scraper is used.
    scraper = scrapers[0]
    symbol_func = symbol_funcs[0]

    # Cancellation doesnot make sense for single scraper
    cancel_function = lambda: False

    # Initial Pass
    instance_func(scraper, symbol_func, result, cancel_function)

    # Get real failures
    failures, data = result.failures, result.data
    failures = {sym: s for sym, s in failures.items() if sym not in data}
    logger.debug(f":: Failed symbols {len(failures)}: {pformat(failures)}")

    # Second Pass: Retry failures once again, using alt scraper if available
    # do it one by one i.e batch_size=1
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

    if len(scrapers) > 1:
        scraper = scrapers[1]
    else:
        scraper = scrapers[0]

    disabled_cancel_func = lambda: False
    scraper.batch_size = 1

    logger.info(":: Reprocessing failures again, one by one.")
    symbol_func = deque(failures.keys()).pop
    instance_func(scraper, symbol_func, result, cancel_func=disabled_cancel_func)

    return result


def cancel_func(symbol_func: Callable[[], str]):
    # check if the symbol_func that fetches next symbol itself is empty
    # Cancellation is only used for proxy scrapers
    # To stop the time waste searching and rotating free proxies when queue is already empty
    return len(symbol_func.__self__) == 0
