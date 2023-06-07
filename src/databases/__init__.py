import os

# Storage directory
DATA_DIR = "./data"


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


from src.databases.sqlitedb import SqliteDB
from src.databases.csvdb import CsvDB
from src.databases.jsondb import JsonDB
