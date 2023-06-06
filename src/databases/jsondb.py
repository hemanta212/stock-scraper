"""Saves data to a json file"""

import os
import json
import loguru
from datetime import datetime
from . import DATA_DIR, ensure_dir


class JsonDB:
    def __init__(self) -> None:
        self.dbpath = os.path.join(DATA_DIR, "database.json")
        ensure_dir(DATA_DIR)
        self.initdb()

    def initdb(self):
        if not os.path.exists(self.dbpath):
            with open(self.dbpath, "w") as f:
                json.dump([], f)

    def save(self, data):
        with open(self.dbpath, "r") as f:
            db = json.load(f)
            db.append(data)
        with open(self.dbpath, "w") as f:
            json.dump(db, f)
        loguru.logger.debug(f":: JsonDB: Saved {data['symbol']} to database.")

    def save_bulk(self, data):
        """Save data of multiple stocks in bulk"""
        with open(self.dbpath, "r") as f:
            db = json.load(f)
            db.extend(data)
        with open(self.dbpath, "w") as f:
            json.dump(db, f)
        loguru.logger.debug(f":: JsonDB: Saved {len(data)} stocks to database.")
