import sys

from loguru import logger


def init_logger(verbose=False):
    """Initialize logger"""
    verbose_config = {
        "handlers": [
            {"sink": sys.stdout},
            {"sink": "file.log"},
        ],
    }
    default_config = {
        "handlers": [
            {
                "sink": sys.stdout,
                "level": "INFO",
                "format": "{time:h:mm:ss:A} {level} {message}",
            },
            {"sink": "file.log"},
        ]
    }
    config = default_config if not verbose else verbose_config
    logger.configure(**config)
