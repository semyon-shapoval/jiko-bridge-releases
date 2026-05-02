"""
Helper module for integration tests.
Code by Semyon Shapoval, 2026
"""

import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='[Test Jiko] %(levelname)s: %(message)s',
)


def get_logger(name: str) -> logging.Logger:
    """Returns a logger instance with the specified name."""
    return logging.getLogger(name)
