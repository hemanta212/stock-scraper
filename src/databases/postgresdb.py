import os
from contextlib import contextmanager
from typing import List

import psycopg2

from src import logger
from src.types import StockInfo


class PostgresDB:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT"),
            database=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
        )
        self.cur = self.conn.cursor()
        self.initdb()

    def initdb(self):
        self.cur.execute(
            """
            CREATE TABLE IF NOT EXISTS stockinfo (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                marketcap BIGINT NOT NULL,
                price REAL NOT NULL,
                volume BIGINT NOT NULL,
                highprice REAL NOT NULL,
                lowprice REAL NOT NULL,
                open REAL NOT NULL,
                prevclose REAL NOT NULL,
                timestamp BIGINT NOT NULL
            )
        """
        )
        self.conn.commit()

    def save(self, data: List[StockInfo]):
        """Save data of multiple stocks in bulk"""
        self.cur.executemany(
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
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        logger.debug(f":: PostgresDB: Saved {len(data)} records to database")
        return self

    def fetch(self, query: str, params=None):
        self.cur.execute(query, params)
        return self.cur.fetchall()

    def close(self):
        self.cur.close()
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
