import loguru

from src.scrapers.yahooapi import YahooAPI
from src.databases.csvdb import CsvDB
from src.databases.jsondb import JsonDB
from src.databases.sqlitedb import SqliteDB


def main():
    scraper = YahooAPI()
    if not scraper.working:
        loguru.logger.error(":: Yahoo API is not working")
        return
    csvdb = CsvDB()
    jsondb = JsonDB()
    sqlitedb = SqliteDB()
    symbol = "GOOG"
    data = scraper.get_data(symbol)
    csvdb.save(data)
    jsondb.save(data)
    sqlitedb.save(data)


if __name__ == "__main__":
    main()
