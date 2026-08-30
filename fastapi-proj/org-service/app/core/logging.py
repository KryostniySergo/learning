import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """setup_logging Настраивает логирование

    Args:
        level (int, optional): Уровень логирования. Defaults to logging.INFO.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
