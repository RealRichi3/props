import logging
from .config import Config
from typing import TypedDict, Literal, Optional
import os


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
        terminalCh = logging.StreamHandler()

        global_config = configMgr.get_section("global")
        print(f"global config {global_config}")

        base_out_dir = global_config["out_dir"]
        print(f"output dir {base_out_dir}")
        timestamp = global_config["timestamp"]
        log_dir_path = os.path.join(base_out_dir, timestamp)

        os.makedirs(log_dir_path, exist_ok=True)

        log_file_path = os.path.join(log_dir_path, f'{options["name"]}.log')

        print(f"Setting log file path: {log_file_path}")
        fileCh = logging.FileHandler(log_file_path)
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        )

        channels = [terminalCh, fileCh]
        for channel in channels:
            channel.setLevel(log_level)
            channel.setFormatter(formatter)
            channel.setLevel(log_level)
            logger.addHandler(channel)

        logger.setLevel(log_level)

    return logger
