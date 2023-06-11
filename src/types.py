from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class StockInfo:
    name: str
    symbol: str
    marketcap: int
    price: float
    volume: int
    highprice: float
    lowprice: float
    open: float
    prevclose: float
    timestamp: int


@dataclass
class Result:
    data: Dict[str, StockInfo]
    failures: Dict[str, str]
