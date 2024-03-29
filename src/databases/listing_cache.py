"""
A sqlite db to keep record of fullnames of stocks with their symbols
"""
import os
import sqlite3
from contextlib import contextmanager
from typing import Dict

from src import logger
from src.databases import DATA_DIR, ensure_dir


class ListingCache:
    def __init__(self):
        self.dbpath = os.path.join(DATA_DIR, "listings.cache")
        ensure_dir(DATA_DIR)
        self.initdb()

    def initdb(self):
        self.conn = sqlite3.connect(self.dbpath)
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS stocklist (
                symbol TEXT PRIMARY KEY NOT NULL,
                name TEXT NOT NULL UNIQUE
            )
        """
        )
        self.conn.commit()

    def get_name(self, symbol: str):
        """
        Get the name of a stock from its symbol
        """
        self.cursor.execute(
            """
            SELECT name FROM stocklist WHERE symbol = ?
        """,
            symbol,
        )
        return self.cursor.fetchone()

    def save(self, data: Dict[str, str]):
        """
        Take a dictionary of symbol and name and update the database
        Check if already present, if not then add
        """
        self.cursor.executemany(
            """
            INSERT OR IGNORE INTO stocklist (
                symbol,
                name
            ) VALUES (?, ?)
        """,
            [(symbol, name) for symbol, name in data.items()],
        )
        self.conn.commit()
        logger.debug(f":: ListDB: Saved {len(data)} stocks to cache.")
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
            logger.exception(e)
        finally:
            db.close()
