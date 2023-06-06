import json
import requests
import loguru


class NYSE:
    def __init__(self) -> None:
        self.url = "https://www.nyse.com/api/quotes/filter"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }

    def list(self):
        # Change post data, until you get all the stocks
        symbols = []
        for i in range(1, 10):
            data = {
                "instrumentType": "EQUITY",
                "pageNumber": i,
                "sortColumn": "NORMALIZED_TICKER",
                "sortOrder": "ASC",
                "maxResultsPerPage": 1001,
                "filterToken": "",
            }
            response = requests.post(self.url, headers=self.headers, json=data)
            if response.status_code == 200:
                data = response.json()
                valid_stocks = [
                    i
                    for i in data
                    if i.get("symbolTicker")
                    and i["symbolTicker"] == i.get("normalizedTicker")
                    and i["micCode"] == "XNYS"
                ]
                for stock in valid_stocks:
                    symbols.append(stock["symbolTicker"])
                # Check if last page or pagination remaining
                if len(data) < 1000:
                    break
            else:
                loguru.logger.error(
                    f":: NYSEListing Error: {response.status_code} {response.text}"
                )

        loguru.logger.debug(f":: NYSEListing: Found {len(symbols)} stocks.")
        with open("./data/nyse.json", "w") as wf:
            json.dump(symbols, wf)
        return symbols
