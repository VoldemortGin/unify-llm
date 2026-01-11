"""
Logging utilities for UnifyLLM.

Provides a cross-platform logger that handles UTF-8 encoding properly on Windows.
"""


from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import rootutils

ROOT_DIR = rootutils.setup_root(search_from=os.getcwd(), indicator=['.project-root'], pythonpath=True)


class UTF8StreamHandler(logging.StreamHandler):
    """
    Custom StreamHandler that handles UTF-8 encoding on Windows.
    Avoids GBK encoding issues while handling closed file scenarios.
    """

    def emit(self, record):
        """Override emit to handle UTF-8 encoding."""
        try:
            msg = self.format(record)
            stream = self.stream

            # Check if stream is closed
            if hasattr(stream, 'closed') and stream.closed:
                return

            # On Windows, try UTF-8 encoding with fallback
            if sys.platform == 'win32':
                try:
                    stream.write(msg + self.terminator)
                    self.flush()
                except UnicodeEncodeError:
                    if hasattr(stream, 'buffer'):
                        encoded = (msg + self.terminator).encode('utf-8', errors='replace')
                        stream.buffer.write(encoded)
                        stream.buffer.flush()
                    else:
                        encoded = (msg + self.terminator).encode('utf-8', errors='replace')
                        stream.write(encoded)
                        self.flush()
            else:
                stream.write(msg + self.terminator)
                self.flush()
        except Exception:
            self.handleError(record)


def setup_logger(
    name: str = "UnifyLLM",
    log_level: str = "INFO",
    log_file: str | None = None
) -> logging.Logger:
    """
    Setup and return a logger.

    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path. If None, only console logging is used.

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Console handler (using custom UTF8StreamHandler)
    console_handler = UTF8StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_file_path = Path(log_file)
        if not log_file_path.is_absolute():
            log_file_path = ROOT_DIR / log_file_path
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Create default logger (console only, can be reconfigured)
logger = setup_logger("UnifyLLM")

__all__ = ['logger', 'setup_logger', 'UTF8StreamHandler']
