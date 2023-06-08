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
from queue import deque

from src import logger


def parallel_executor(instance_func, scrapers, symbol_funcs):
    result = {
        "data": [],
        "failures": {},
    }

    # check if the symbol_func that fetches next symbol itself is empty
    # Cancellation is only used for proxy scrapers
    # To stop the time waste searching and rotating free proxies when queue is already empty
    def cancel_func(symbol_func, scraper):
        print("EE", len(symbol_func.__self__))
        return len(symbol_func.__self__) == 0 and scraper.use_proxy

    cancel_funcs = [
        partial(cancel_func, symbol_func, scraper)
        for scraper, symbol_func in zip(scrapers, symbol_funcs)
    ]

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

    failures = result["failures"]
    logger.debug(f":: Failed symbols {len(failures)}: {pformat(failures)}")

    final_result = {
        "data": result["data"],
        "failures": {},
    }

    # Second Pass: Retry failures with alternate scraper, and disable cancellation
    disabled_cancel_func = lambda: False
    logger.info(":: Reprocessing failures with alternate scraper")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        scrapers_symbols = match_scrapers_failures(scrapers, failures)
        futures = [
            executor.submit(
                instance_func, scraper, symbol_func, final_result, disabled_cancel_func
            )
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
    # list of scrapers ['YahooAPI', 'StockAnalaysisAPI']
    scraper_names = list(set([repr(scraper) for scraper in scrapers]))

    # map name to deque, and fill the deque
    scraper_names_map = {scraper_name: deque() for scraper_name in scraper_names}

    # makes {'sym1': 'A', 'sym2': 'A'] -> {'A': (sym1, sym2)}
    for symbol, scraper_name in failures.items():
        scraper_names_map[scraper_name].append(symbol)

    scrapers_failures = {}
    # assign deques to other scraper, which is one index above.
    for scraper in scrapers:
        scraper_name = repr(scraper)

        # Find key whose deque values to take
        assign_index = (scraper_names.index(scraper_name) + 1) % len(scraper_names)
        assign_key = scraper_names[assign_index]
        deque_symbol = scraper_names_map[assign_key]

        # Assign symbol func for scraper
        # If non proxy version of scraper available donot assign proxy version
        is_proxy = scraper.use_proxy
        non_proxy_available = [
            s for s in scrapers if repr(s) == repr(scraper) and not s.use_proxy
        ]
        if is_proxy and non_proxy_available:
            continue
        else:
            scrapers_failures[scraper] = deque_symbol.pop

    return scrapers_failures
