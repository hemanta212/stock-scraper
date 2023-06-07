"""SQLITE DATABASE"""
import sqlite3
import os
import json
import loguru
from datetime import datetime
from src.databases import DATA_DIR, ensure_dir


class SqliteDB:
    def __init__(self):
        self.dbpath = os.path.join(DATA_DIR, "database.sqlite")
        ensure_dir(DATA_DIR)
        self.conn = sqlite3.connect(self.dbpath)
        self.cursor = self.conn.cursor()
        self.initdb()

    def initdb(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS stockinfo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                marketcap INTEGER NOT NULL,
                price REAL NOT NULL,
                volume INTEGER NOT NULL,
                highprice REAL NOT NULL,
                lowprice REAL NOT NULL,
                open REAL NOT NULL,
                prevclose REAL NOT NULL,
                timestamp INTEGER NOT NULL
            )
        """
        )
        self.conn.commit()

    def save(self, data):
        self.cursor.execute(
            """
            INSERT INTO stockinfo (
                name,
                symbol,
                marketcap,
                price,
                volume,
                highprice,
                lowprice,
                open,
                prevclose,
                timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                data["name"],
                data["symbol"],
                data["marketcap"],
                data["price"],
                data["volume"],
                data["highprice"],
                data["lowprice"],
                data["open"],
                data["prevclose"],
                data["timestamp"],
            ),
        )
        self.conn.commit()
        loguru.logger.debug(f":: SqliteDB: Saved {data['symbol']} to database.")

    def save_bulk(self, data):
        """Save data of multiple stocks in bulk"""
        self.cursor.executemany(
            """
            INSERT INTO stockinfo (
                name,
                symbol,
                marketcap,
                price,
                volume,
                highprice,
                lowprice,
                open,
                prevclose,
                timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                (
                    d["name"],
                    d["symbol"],
                    d["marketcap"],
                    d["price"],
                    d["volume"],
                    d["highprice"],
                    d["lowprice"],
                    d["open"],
                    d["prevclose"],
                    d["timestamp"],
                )
                for d in data
            ],
        )
        self.conn.commit()
        loguru.logger.debug(f":: SqliteDB: Saved {len(data)} stocks to database.")
