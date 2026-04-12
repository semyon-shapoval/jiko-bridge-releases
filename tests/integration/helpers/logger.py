import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='[Test Jiko] %(levelname)s: %(message)s',
)

def get_logger(name: str) -> logging.Logger:
		return logging.getLogger(name)