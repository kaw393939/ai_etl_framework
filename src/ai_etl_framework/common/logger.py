# First, let's add LoggingConfig to settings.py

# Add logging config to AppConfig


import logging
import sys
from pathlib import Path
from datetime import datetime

from ai_etl_framework.config.settings import config

def setup_logger(name: str = None) -> logging.Logger:
    """
    Set up and configure a logger instance.

    Args:
        name: Logger name (defaults to the root logger if None)

    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    logs_dir = config.directory.logs_dir
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Get log level from config
    log_level = config.logging.level.upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Create or get the logger
    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)

    # Avoid adding multiple handlers to the logger
    if not getattr(logger, '_handler_set', False):
        logger._handler_set = True  # Custom attribute to prevent re-adding handlers

        # File handler
        log_filename = f"{datetime.now().strftime(config.logging.date_format)}_{config.logging.file_name}"
        log_file = logs_dir / log_filename
        file_handler = logging.FileHandler(
            log_file,
            encoding=config.logging.encoding
        )
        file_handler.setLevel(numeric_level)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)

        # Create formatter and add it to the handlers
        formatter = logging.Formatter(config.logging.format)
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger