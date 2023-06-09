import sys
from pprint import pformat
from typing import Deque, List

from dotenv import load_dotenv

from src import logger
from src.databases import DBType, PostgresDB, SqliteDB
from src.listings import listings_map
from src.runners import executor, parallel_executor
from src.scrapers import ScraperType, StockAnalysisAPI, YahooAPI, scraper_instance


def main(symbols: Deque[str]):
    """
    Takes in a Deque of symbols to scrape, distributes them to scrapers.
    Runs scraping tasks in parallel. Saves scraped data to databases.
    """
    dbs: List[DBType] = [
        PostgresDB,
        SqliteDB,
    ]
    scrapers: List[ScraperType] = [
        YahooAPI(batch_size=10, rate_limit=1.0),
        YahooAPI(batch_size=10, use_proxy=True, rate_limit=0.5),
        StockAnalysisAPI(batch_size=1, rate_limit=0.3),
    ]
    symbol_access_funcs = [
        symbols.pop,
        symbols.popleft,
        symbols.popleft,
    ]

    all_data, failures = parallel_executor(
        scraper_instance, scrapers, symbol_access_funcs
    )

    logger.info(f":: Scraped {len(all_data)} stocks data.")
    logger.info(f":: Failed stocks {len(failures)}: {pformat(failures)}")

    if not all_data:
        logger.error(":: No data scraped. Exiting.")
        return

    for db_class in dbs:
        try:
            with db_class.session() as db:
                db.save(all_data)
        except Exception as e:
            logger.error(f":: Failed to connect to {db_class.__name__}: {e}")

    logger.info(f":: Saving to databases complete!")


if __name__ == "__main__":
    load_dotenv()
    from src import init_logger

    args = sys.argv

    # Parse verbosity and help flags
    verbose = "-v" in args or "--verbose" in args
    help = "-h" in args or "--help" in args
    init_logger(verbose=verbose)

    # Pase stock listing
    listing_arg = sys.argv[1] if len(sys.argv) > 1 else "nasdaq100"
    # Get fetcher class from listing string
    symbols_fetcher = listings_map.get(listing_arg)

    # Help information
    if symbols_fetcher is None or help:
        logger.info(f":: Usage: {', '.join(list(listings_map.keys()))}")
        sys.exit(1)

    # Try to scrape listings from fetcher
    try:
        symbols = symbols_fetcher().queue()
    except Exception as e:
        logger.exception(f":: Failed getting listings for {listing_arg} {e}")
        sys.exit(1)

    logger.info(f":: Fetching {len(symbols)} stocks from {listing_arg}")
    main(symbols)
