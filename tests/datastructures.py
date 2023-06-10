import requests

from src.scrapers import StockAnalysisAPI, YahooAPI
from src.types import StockInfo
from src.utils.proxy import RequestProxy


class CRequestProxy(RequestProxy):
    def __init__(self, response=None):
        super().__init__()
        self.response = response

    def request(
        self,
        method: str,
        url: str,
        cancel_func,
        tries: int = 0,
        timeout: int = 5,
        **kwargs,
    ):
        return self.response


class CYahooAPI(YahooAPI):
    def __init__(self, response):
        super().__init__()
        self.cookie_cred = {"cookie": {}, "crumb": ""}
        self.session = CRequestProxy(response=response)


class CustomResponse(requests.Response):
    def __init__(
        self,
        status_code=200,
        content="",
        replace_json=None,
        replace_result=None,
        result_kwargs={},
        error=None,
        result_num=1,
    ):
        super().__init__()
        self.status_code = status_code
        self._content = content
        self.result_kwargs = result_kwargs
        self.replace_json = replace_json
        self.replace_result = replace_result
        self.error = error
        self.result_num = result_num

    def json(self):
        data = {"quoteResponse": {"error": self.error, "result": []}}
        if self.replace_json is not None:
            return self.replace_json
        elif self.replace_result is not None:
            data["quoteResponse"]["result"] = self.replace_result
            return data
        data["quoteResponse"]["result"] = [self.result_kwargs]
        data["quoteResponse"]["result"][0].update(self.default_data())

        # how many results objects to send
        if self.result_num > 1:
            result = data["quoteResponse"]["result"][0]
            for i in range(1, self.result_num):
                data["quoteResponse"]["result"].append(result)

        return data

    def default_data(self):
        return {
            "cryptoTradeable": False,
            "currency": "USD",
            "customPriceAlertConfidence": "HIGH",
            "exchange": "NYQ",
            "exchangeDataDelayedBy": 0,
            "exchangeTimezoneName": "America/New_York",
            "exchangeTimezoneShortName": "EDT",
            "fiftyTwoWeekHigh": {"fmt": "117.25", "raw": 117.25},
            "fiftyTwoWeekHighChange": {"fmt": "-0.43", "raw": -0.4300003},
            "fiftyTwoWeekHighChangePercent": {"fmt": "-0.37%", "raw": -0.00366738},
            "fiftyTwoWeekLow": {"fmt": "115.02", "raw": 115.02},
            "fiftyTwoWeekLowChange": {"fmt": "1.80", "raw": 1.800003},
            "fiftyTwoWeekLowChangePercent": {"fmt": "1.56%", "raw": 0.015649479},
            "fiftyTwoWeekRange": {"fmt": "115.02 - 117.25", "raw": "115.02 - 117.25"},
            "firstTradeDateMilliseconds": 528039000000,
            "fullExchangeName": "NYSE",
            "gmtOffSetMilliseconds": -14400000,
            "language": "en-US",
            "longName": "Fiserv, Inc.",
            "market": "us_market",
            "marketState": "CLOSED",
            "marketCap": {
                "fmt": "75.572B",
                "longFmt": "75,572,000,000",
                "raw": 75572000000,
            },
            "name": "Fiserv, Inc.",
            "priceHint": 2,
            "quoteType": "EQUITY",
            "region": "US",
            "regularMarketDayHigh": {"fmt": "117.25", "raw": 117.25},
            "regularMarketDayLow": {"fmt": "115.02", "raw": 115.02},
            "regularMarketDayRange": {
                "fmt": "115.02 - 117.25",
                "raw": "115.02 - 117.25",
            },
            "regularMarketOpen": {"fmt": "115.81", "raw": 115.81},
            "regularMarketPreviousClose": {"fmt": "115.29", "raw": 115.29},
            "regularMarketPrice": {"fmt": "116.82", "raw": 116.82},
            "regularMarketTime": {"fmt": "4:03PM EDT", "raw": 1686340993},
            "regularMarketVolume": {
                "fmt": "2.57M",
                "longFmt": "2,570,006",
                "raw": 2570006,
            },
            "shortName": "Fiserv, Inc.",
            "sourceInterval": 15,
            "symbol": "FI",
            "tradeable": False,
            "triggerable": True,
            "typeDisp": "Equity",
        }


StandardStockInfoValues = dict(
    name="Fiserv, Inc.",
    symbol="FI",
    marketcap=75572000000,
    price=116.82,
    volume=2570006,
    highprice=117.25,
    lowprice=115.02,
    open=115.81,
    prevclose=115.29,
    timestamp=1686340993,
)

StandardStockInfo = StockInfo(**StandardStockInfoValues)
