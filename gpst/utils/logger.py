import logging
import os


_logger = logging.getLogger(__name__)

TRACE_LEVEL = 5


def setup_logger() -> None:
    log_level = logging.INFO
    dbg = os.getenv("DEBUG", "0")
    if dbg == "1":
        log_level = logging.DEBUG
    elif dbg >= "2":
        log_level = logging.NOTSET
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    logging.addLevelName(TRACE_LEVEL, "TRACE")



class logger:
    @staticmethod
    def trace(message: str) -> None:
        _logger.log(5, message)

    @staticmethod
    def debug(message: str) -> None:
        _logger.debug(message)

    @staticmethod
    def info(message: str) -> None:
        _logger.info(message)

    @staticmethod
    def warning(message: str) -> None:
        _logger.warning(message)

    @staticmethod
    def error(message: str) -> None:
        _logger.error(message)

    @staticmethod
    def critical(message: str) -> None:
        _logger.critical(message)
