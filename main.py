import sys
from pprint import pformat

from dotenv import load_dotenv

from src import logger
from src.databases import PostgresDB, SqliteDB
from src.listings import listings_map
from src.runners.thread import parallel_executor
from src.scrapers import StockAnalysisAPI, YahooAPI
from src.utils.validator import is_valid_stock


def main(symbols):
    dbs = (
        PostgresDB,
        SqliteDB,
    )
    scrapers = (
        YahooAPI(rate_limit=1.0),
        YahooAPI(use_proxy=True, rate_limit=0.5),
        StockAnalysisAPI(use_proxy=True, rate_limit=0.3),
        StockAnalysisAPI(rate_limit=0.3),
    )
    symbol_funcs = (
        symbols.pop,
        symbols.popleft,
        symbols.pop,
        symbols.popleft,
    )

    all_data, failures = parallel_executor(create_scraper, scrapers, symbol_funcs)

    print(f":: Scraped {len(all_data)} stocks data.")
    print(f":: Failed stocks {len(failures)}: {pformat(failures)}")

    if not all_data:
        logger.error(":: No data to save")
        return

    for db in dbs:
        db = db()
        try:
            db.save(all_data)
        except Exception as e:
            logger.exception(f":: Failed save to db {db}: {e}")
        finally:
            db.close()

    print(f":: Saved to all databases.")


def create_scraper(scraper, symbol_func, result, cancel_func):
    """
    Specifies how a scraper instances operates
    We're going to spin up multiple of these.

    scraper_class: The scraper to use in this instance
    symbol_func: A function to get next symbol to scrape
    result: Sink to submit scraped data and failures
    """
    # start scraper
    scraper.setup()

    index = 0
    while True:
        if not scraper.working:
            logger.error(f":: {scraper} is not working. Ending thread.")
            break

        if cancel_func():
            logger.debug(f":: Cancellation Signal {scraper}: No more symbols to scrape")
            break

        symbols = []
        for _ in range(scraper.batch_size):
            try:
                symbols.append(symbol_func())
            except IndexError:
                # Deque empty
                logger.debug(f":: {scraper} Queue empty: No more symbols to scrape")
                break

        if not symbols:
            break

        try:
            data = scraper.get_data(symbols, cancel_func=cancel_func)
        except Exception as e:
            logger.exception(f":: {scraper}: {e}")
            data = [None for _ in symbols]

        for stock_data, symbol in zip(data, symbols):
            if stock_data and is_valid_stock(stock_data):
                result["data"].append(stock_data)
                index += 1
                logger.debug(f":: {scraper}: Added {symbol} | {index}")
            else:
                logger.warning(f":: {scraper}: Failed {symbol} | {index}")
                result["failures"].update({symbol: repr(scraper)})


if __name__ == "__main__":
    load_dotenv()

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
        logger.exception(f":: Failed getting listings for {listing_arg} {e}")
        sys.exit(1)

    logger.debug(f":: Fetching {len(symbols)} stocks from {listing_arg}")

    main(symbols)
