import loguru
import concurrent.futures

from src.scrapers.yahooapi import YahooAPI
from src.databases import CsvDB, JsonDB, SqliteDB
from src.listings import DowJones30, Nasdaq100, SandP500, NYSE


def main():
    dbs = [CsvDB(), JsonDB(), SqliteDB()]
    symbol_list = Nasdaq100().list()
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

    print(f"Failed symbols: {failures}")


def create_scraper(symbol_list, all_data, failures):
    scraper = YahooAPI()
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
    main()
