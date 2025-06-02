# sdk/utils/logger.py
import logging
import logging.config

DEFAULT_LOGGING_DICT = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "std": {"format": "[%(levelname)s] %(asctime)s %(name)s: %(message)s"}
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "std",
            "stream": "ext://sys.stdout",
        }
    },
    "loggers": {
        "moderntensor": {"level": "DEBUG", "handlers": ["console"], "propagate": False}
    },
}


def init_logging(custom_config=None):
    # Merge custom_config (if any) with DEFAULT_LOGGING_DICT
    config = DEFAULT_LOGGING_DICT.copy()
    if custom_config:
        # Merging logic, tuỳ bạn triển khai
        pass
    logging.config.dictConfig(config)
