from queue import deque
import concurrent.futures
import math
import sys

import loguru

from src.databases import CsvDB, JsonDB, SqliteDB
from src.listings import listings_map
from src.scrapers import StockAnalysisAPI, YahooAPI


def main(symbols):
    dbs = [CsvDB(), JsonDB(), SqliteDB()]
    all_data, failures = [], {}

    # Initial Pass
    with concurrent.futures.ThreadPoolExecutor() as executor:
        symbol_funcs = [symbols.pop, symbols.popleft]
        scrapers = [YahooAPI, StockAnalysisAPI]
        futures = [
            executor.submit(
                create_scraper, scraper, symbol_func, all_data, failures, use_proxy=True
            )
            for scraper, symbol_func in zip(scrapers, symbol_funcs)
        ]
        for future in concurrent.futures.as_completed(futures):
            future.result()

    # TODO: ONly do this if failures are present, refactor to separate fucntions
    # Second Pass: Retry failures with alternate scraper
    loguru.logger.info(":: Reprocessing Failures with alternate scraper")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        scrapers = [StockAnalysisAPI, YahooAPI]
        scrapers_symbols = match_scrapers_failures(scrapers, failures)
        futures = [
            executor.submit(
                create_scraper, scraper, symbol_func, all_data, failures, use_proxy=True
            )
            for scraper, symbol_func in scrapers_symbols.items()
        ]
        for future in concurrent.futures.as_completed(futures):
            future.result()

    if all_data:
        for db in dbs:
            db.save_bulk(all_data)

    print(f":: Failed symbols: {failures}")


def create_scraper(scraper_class, symbol_func, all_data, failures, use_proxy=True):
    scraper = scraper_class(use_proxy=use_proxy)
    if not scraper.working:
        loguru.logger.error(":: Yahoo API is not working")
        return

    index = 0
    while True:
        try:
            symbol = symbol_func()
        except IndexError:
            # pop from empty deque
            break

        data = scraper.get_data(symbol)
        if data is not None:
            all_data.append(data)
            index += 1
            loguru.logger.debug(
                f":: {scraper_class.__name__}: Added {symbol} | {index}"
            )
        else:
            failures[symbol] = scraper_class.__name__


def divide_symbols(symbol_list, buckets):
    """Divides the list of symbols into Exactly given buckets"""
    # divide the list l into lists of size n
    l, n = symbol_list, math.ceil(len(symbol_list) / buckets)
    for i in range(0, len(l), n):
        yield l[i : i + n]


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


if __name__ == "__main__":
    listing_arg = sys.argv[1] if len(sys.argv) > 1 else "nasdaq100"

    symbols_fetcher = listings_map.get(listing_arg)
    if symbols_fetcher is None:
        loguru.logger.error(f":: Main: Invalid Stock list: {listing_arg}")
        sys.exit(1)

    symbols = symbols_fetcher().queue()
    loguru.logger.debug(f":: Fetching {len(symbols)} stocks from {listing_arg}")

    main(symbols)
