import os

# Storage directory
DATA_DIR = "./data"


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


from .sqlitedb import SqliteDB
from .csvdb import CsvDB
from .jsondb import JsonDB
