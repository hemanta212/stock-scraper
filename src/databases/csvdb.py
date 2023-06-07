import os
import csv
from src import logger
from src.databases import DATA_DIR, ensure_dir


class CsvDB:
    def __init__(self) -> None:
        self.dbpath = os.path.join(DATA_DIR, "database.csv")
        ensure_dir(DATA_DIR)
        self.columns = [
            "name",
            "symbol",
            "marketcap",
            "price",
            "volume",
            "highprice",
            "lowprice",
            "open",
            "prevclose",
            "timestamp",
        ]
        self.initdb()

    def initdb(self):
        if not os.path.exists(self.dbpath):
            with open(self.dbpath, "w") as f:
                writer = csv.DictWriter(f, fieldnames=self.columns)
                writer.writeheader()

    def save(self, data):
        with open(self.dbpath, "a") as f:
            writer = csv.DictWriter(f, fieldnames=self.columns)
            writer.writerow(data)
        logger.debug(f":: CsvDB: Saved {data['symbol']} to database.")
        return self

    def save_bulk(self, data):
        """Save data of multiple stocks in bulk"""
        with open(self.dbpath, "a") as f:
            writer = csv.DictWriter(f, fieldnames=self.columns)
            writer.writerows(data)
        logger.debug(f":: CsvDB: Saved {len(data)} stocks to database.")
        return self

    def close(self):
        pass
