import sys
from functools import partial
from pprint import pformat

from src import logger
from src.databases import CsvDB, JsonDB, SqliteDB
from src.listings import listings_map
from src.runners.threading import parallel_executor
from src.scrapers import StockAnalysisAPI, YahooAPI
from src.utils.validator import is_valid


def main(symbols):
    scrapers = (
        partial(YahooAPI, use_proxy=True),
        partial(StockAnalysisAPI, use_proxy=True, rate_limit=0.3),
    )
    symbols_access_funcs = (
        symbols.pop,
        symbols.popleft,
    )

    all_data, failures = parallel_executor(
        create_scraper, scrapers, symbols_access_funcs
    )

    print(f":: Scraped {len(all_data)} stocks data.")
    print(f":: Failed stocks {len(failures)}: {pformat(failures)}")

    dbs = (
        CsvDB,
        JsonDB,
        SqliteDB,
    )
    if all_data:
        for db in dbs:
            db().save_bulk(all_data).close()
    print(f":: Saved to all databases.")


def create_scraper(scraper_class, symbol_func, result):
    """
    Specifies how a scraper instances operates
    We're going to spin up multiple of these.

    scraper_class: The scraper to use in this instance
    symbol_func: A function to get next symbol to scrape
    result: Sink to submit scraped data and failures
    """
    scraper = scraper_class()

    if not scraper.working:
        logger.error(f":: {scraper} is not working")
        return

    index = 0
    while True:
        try:
            symbol = symbol_func()
        except IndexError:
            # pop from empty deque
            break

        try:
            data = scraper.get_data(symbol)
        except Exception as e:
            logger.error(f":: {scraper}: {e}")
            data = None

        if data and is_valid(data):
            result["data"].append(data)
            index += 1
            logger.debug(f":: {scraper}: Added {symbol} | {index}")
        else:
            result["failures"].update({symbol: repr(scraper)})


if __name__ == "__main__":
    listing_arg = sys.argv[1] if len(sys.argv) > 1 else "nasdaq100"

    # Get fetcher class from listing string
    symbols_fetcher = listings_map.get(listing_arg)
    if symbols_fetcher is None or listing_arg in ("--help", "-h"):
        logger.info(f":: Usage: {', '.join(list(listings_map.keys()))}")
        sys.exit(1)

    # Try to scrape listings from fetcher
    try:
        symbols = symbols_fetcher().queue()
    except Exception as e:
        logger.error(f":: Failed getting listings for {listing_arg} {e}")
        sys.exit(1)

    logger.debug(f":: Fetching {len(symbols)} stocks from {listing_arg}")
    main(symbols)
