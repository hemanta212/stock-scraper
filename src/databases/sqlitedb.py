"""SQLITE DATABASE"""
import os
import sqlite3
from contextlib import contextmanager
from typing import List

from src import logger
from src.databases import DATA_DIR, ensure_dir
from src.types import StockInfo


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

    def save(self, data: List[StockInfo]):
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
                    d.name,
                    d.symbol,
                    d.marketcap,
                    d.price,
                    d.volume,
                    d.highprice,
                    d.lowprice,
                    d.open,
                    d.prevclose,
                    d.timestamp,
                )
                for d in data
            ],
        )
        self.conn.commit()
        logger.info(f":: SqliteDB: Saved {len(data)} stocks to database.")
        return self

    def close(self):
        self.conn.close()

    @classmethod
    @contextmanager
    def session(cls):
        """Context manager for database session"""
        db = cls()
        try:
            yield db
        except Exception as e:
            logger.debug(e)
        finally:
            db.close()
