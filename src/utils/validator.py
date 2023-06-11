"""
Validate the stock information as it is scraped
"""
from src import logger
from src.types import StockInfo


def is_valid_stock(stock_info: StockInfo):
    field_types = {
        "name": (str,),
        "symbol": (str,),
        "marketcap": (int,),
        "price": (int, float),
        "volume": (int,),
        "highprice": (int, float),
        "lowprice": (int, float),
        "open": (int, float),
        "prevclose": (int, float),
        "timestamp": (int,),
    }

    for field, expected_types in field_types.items():
        value = getattr(stock_info, field)
        # type check, null check
        if not isinstance(value, expected_types):
            expected_types_str = " or ".join(t.__name__ for t in expected_types)
            logger.error(
                f":: Validation Error: Invalid data type for '{field}'. "
                f"Expected: {expected_types_str}, Got: {type(value).__name__}:'{value}' "
            )
            return False

        # Value <= 0 Check
        if issubclass(float, expected_types) or issubclass(int, expected_types):
            if value <= float(0):
                logger.error(
                    f":: Validation Error: Invalid value for '{field}'. "
                    f"Expected: > 0, Got: {value}"
                )
                return False

        # Empty string and N/A check
        if issubclass(str, expected_types):
            if not value.strip() or value.strip().upper() == "N/A":
                logger.error(
                    f":: Validation Error: Invalid value for '{field}'. "
                    f"Expected: non-empty string, Got: '{value}'"
                )
                return False

    return True
