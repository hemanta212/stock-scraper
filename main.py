import sys
import loguru
import concurrent.futures

from src.scrapers.yahooapi import YahooAPI
from src.databases import CsvDB, JsonDB, SqliteDB
from src.listings import listings_map


def main(symbol_list):
    dbs = [CsvDB(), JsonDB(), SqliteDB()]
    all_data, failures = [], []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        symbols_division = (
            symbol_list[: len(symbol_list) // 2],
            symbol_list[len(symbol_list) // 2 :],
        )
        futures = [
            executor.submit(create_scraper, symbol, all_data, failures)
            for symbol in symbols_division
        ]
        for future in concurrent.futures.as_completed(futures):
            future.result()

    if all_data:
        for db in dbs:
            db.save_bulk(all_data)

    print(f":: Failed symbols: {failures}")


def create_scraper(symbol_list, all_data, failures, use_proxy=True):
    scraper = YahooAPI(use_proxy=use_proxy)
    if not scraper.working:
        loguru.logger.error(":: Yahoo API is not working")
        failures.extend(symbol_list)
        return
    for index, symbol in enumerate(symbol_list):
        data = scraper.get_data(symbol)
        if data is not None:
            all_data.append(data)
            loguru.logger.debug(f":: Main: Added {symbol} {index+1}/{len(symbol_list)}")
        else:
            failures.append(symbol)


if __name__ == "__main__":
    listing_arg = sys.argv[1] if len(sys.argv) > 1 else "nasdaq100"
    symbol_list_fetcher = listings_map.get(listing_arg)
    if symbol_list_fetcher is None:
        loguru.logger.error(f":: Main: Invalid Stock list: {listing_arg}")
        sys.exit(1)
    symbol_list = symbol_list_fetcher().list()
    loguru.logger.debug(f":: Fetching {len(symbol_list)} stocks from {listing_arg}")
    symbol_list = ["NKE"]
    main(symbol_list)
