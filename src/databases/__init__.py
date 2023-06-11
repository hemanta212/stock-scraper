"""
Host both database utilities and database classes for easier import in other files

Warning, circular imports, need to be careful. The ordering is important
- Listing cache imports datadir, ensuredir so it needs to be imported after

isort:skip_file
"""
from typing import Type, Dict
import os

# Storage directory
DATA_DIR = "./data"


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


from src.databases.listing_cache import ListingCache


def cache_listings(symbols: Dict[str, str]):
    with ListingCache.session() as db:
        db.save(symbols)


from src.databases.postgresdb import PostgresDB
from src.databases.sqlitedb import SqliteDB

DBType = Type[PostgresDB] | Type[SqliteDB]
