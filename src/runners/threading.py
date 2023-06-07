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

import math
import concurrent.futures
from queue import deque
from src import logger


def parallel_executor(instance_func, scrapers, symbol_funcs):
    result = {
        "data": [],
        "failures": {},
    }
    # Initial Pass
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(instance_func, scraper, symbol_func, result)
            for scraper, symbol_func in zip(scrapers, symbol_funcs)
        ]
        for future in concurrent.futures.as_completed(futures):
            future.result()

    failures = result["failures"]
    logger.debug(f":: Failed symbols {len(failures)}: {failures}")

    final_result = {
        "data": result["data"],
        "failures": {},
    }
    # Second Pass: Retry failures with alternate scraper
    logger.info(":: Reprocessing failures with alternate scraper")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        scrapers_symbols = match_scrapers_failures(scrapers, failures)
        futures = [
            executor.submit(instance_func, scraper, symbol_func, final_result)
            for scraper, symbol_func in scrapers_symbols.items()
            if failures
        ]
        for future in concurrent.futures.as_completed(futures):
            future.result()

    return final_result["data"], final_result["failures"]


def match_scrapers_failures(scrapers, failures):
    """
    When a stock fetch fails, its symbol and scraper used gets documented
    Here we try to read it, and assign symbol to different scraper
    """
    scrapers_failures = {}
    for scraper in scrapers:
        symbols = [
            symbol
            for symbol, scraper_name in failures.items()
            if scraper.__name__ != scraper_name
        ]
        scrapers_failures[scraper] = deque(symbols).pop
    return scrapers_failures
