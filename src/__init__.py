import sys

from loguru import logger

config = {
    "handlers": [
        {"sink": sys.stdout, "level": 0},
        {"sink": "file.log", "serialize": True},
    ],
    "extra": {"user": "someone"},
}
logger.configure(**config)
