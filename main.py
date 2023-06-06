import loguru

from src.scrapers.yahooapi import YahooAPI
from src.databases import CsvDB, JsonDB, SqliteDB
from src.listings import DowJones30, Nasdaq100, SandP500, NYSE


def main():
    scraper = YahooAPI()
    dbs = [CsvDB(), JsonDB(), SqliteDB()]
    if not scraper.working:
        loguru.logger.error(":: Yahoo API is not working")
        return

    symbol_list = NYSE().list()[1155:]
    all_data = []
    failed_symbols = []
    for index, symbol in enumerate(symbol_list):
        data = scraper.get_data(symbol)
        if data is not None:
            all_data.append(data)
            loguru.logger.debug(f":: Main: Added {symbol} {index+1}/{len(symbol_list)}")
        else:
            failed_symbols.append(symbol)

    if all_data:
        for db in dbs:
            db.save_bulk(all_data)

    print(f"Failed symbols: {failed_symbols}")


if __name__ == "__main__":
    main()
