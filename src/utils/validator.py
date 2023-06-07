"""
Validate the stock information as it is scraped
"""
from src import logger
from src.databases import SqliteDB


def is_valid(stock_info):
    field_types = {
        "name": str,
        "symbol": str,
        "marketcap": int,
        "price": (int, float),
        "volume": int,
        "highprice": (int, float),
        "lowprice": (int, float),
        "open": (int, float),
        "prevclose": (int, float),
        "timestamp": int,
    }

    for field, expected_types in field_types.items():
        value = stock_info.get(field)
        if not isinstance(value, expected_types):
            expected_types_str = " or ".join(t.__name__ for t in expected_types)
            logger.error(
                f":: Validation Error: Invalid data type for '{field}'. "
                f"Expected: {expected_types_str}, Got: {type(value).__name__}:'{value}' "
            )
            return False
    return True
