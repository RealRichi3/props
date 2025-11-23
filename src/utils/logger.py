import logging
from .config import Config
from typing import TypedDict, Literal, Optional


class LoggerOptions(TypedDict):
    level: Optional[Literal[logging.INFO, logging.DEBUG, logging.WARN, logging.ERROR]]
    name: str


def new_logger(options: LoggerOptions, configMgr: Config = Config()) -> logging.Logger:
    logger = logging.getLogger(options["name"])
    log_level = (
        options.get("level")
        if options.get("level")
        else configMgr.get_section("logging")["log_level"]
    )

    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(log_level)

        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        )
        ch.setFormatter(formatter)

        logger.addHandler(ch)

        logger.setLevel(log_level)

    return logger
