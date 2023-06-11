from typing import Callable

from src import logger
from src.scrapers import ScraperType
from src.types import Result
from src.utils.validator import is_valid_stock


def scraper_instance(
    scraper: ScraperType,
    symbol_func: Callable[[], str],
    result: Result,
    cancel_func: Callable[[], bool],
) -> None:
    """
    Specifies how a scraper instances operates
    We're going to spin up multiple of these.

    scraper_class: The scraper to use in this instance
    symbol_func: A function to get next symbol to scrape
    result: Sink to submit scraped data and failures
    """
    # start scraper
    logger.info(f":: Starting scraper {scraper}...")
    scraper.setup(cancel_func=cancel_func)

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
            symbol_data = scraper.get_data(symbols, cancel_func=cancel_func)
        except Exception as e:
            logger.exception(f":: {scraper}: {e}")
            result.failures.update({symbol: repr(scraper) for symbol in symbols})
            continue

        for symbol, stock_data in symbol_data.items():
            if stock_data and is_valid_stock(stock_data):
                result.data.update({symbol: stock_data})
                index += 1
                logger.debug(f":: {scraper}: Added {symbol} | {index}")
            else:
                logger.warning(f":: {scraper}: Failed {symbol} | {index}")
                result.failures.update({symbol: repr(scraper)})

        logger.info(f":: Status: {len(symbol_func.__self__)} Symbols left.. ")
