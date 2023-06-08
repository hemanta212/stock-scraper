"""
Host both database utilities and database classes for easier import in other files

Warning, circular imports, need to be careful. The ordering is important
- Listing cache imports datadir, ensuredir so it needs to be imported after

isort:skip_file
"""
import os

# Storage directory
DATA_DIR = "./data"


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


from src.databases.listing_cache import ListingCache


def cache_listings(symbols):
    db = ListingCache()
    db.save(symbols)
    db.close()


from src.databases.postgresdb import PostgresDB
from src.databases.sqlitedb import SqliteDB
