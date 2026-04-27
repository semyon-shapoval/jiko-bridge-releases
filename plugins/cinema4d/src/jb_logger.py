"""
Logger module for Jiko Bridge Cinema 4D plugin.
Code by Semyon Shapoval, 2026
"""

import logging

def get_logger(name: str) -> logging.Logger:
    """Return a logger"""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "[Jiko Bridge] %(levelname)s [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)
    logger.addHandler(console)

    return logger
