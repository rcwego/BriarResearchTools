# custom_formatter.py

import logging

RESET = "\033[0m"
YELLOW = "\033[33m"
RED = "\033[31m"
BOLD_GREEN = "\033[1;32m"
BOLD_RED = "\033[1;31m"

class CustomFormatter(logging.Formatter):
    """Tilpasset formatter for farger basert på loggnivå."""
    
    # Farger for hvert loggnivå
    FORMATS = {
        logging.DEBUG: "%(message)s",
        logging.INFO: "%(message)s",
        logging.WARNING: YELLOW + "%(levelname)s - %(message)s" + RESET,
        logging.ERROR: RED + "%(levelname)s - %(message)s" + RESET,
        logging.CRITICAL: BOLD_GREEN + "%(levelname)s - %(message)s" + RESET,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, "%(message)s")
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
