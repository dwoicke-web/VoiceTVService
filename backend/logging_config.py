"""
Structured logging configuration for VoiceTV backend
Provides production-ready logging with proper formatting, levels, and file rotation
"""

import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging(app=None, log_level=None):
    """
    Setup structured logging for the application

    Args:
        app: Flask application instance (optional, for Flask context)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                   Defaults to INFO, or DEBUG if FLASK_ENV=development

    Returns:
        Configured logger instance
    """

    # Determine log level from environment or parameter
    if log_level is None:
        env = os.getenv('FLASK_ENV', 'production')
        log_level = logging.DEBUG if env == 'development' else logging.INFO

    # Create logs directory if it doesn't exist
    log_dir = Path('/home/orangepi/Apps/VoiceTVService/logs')
    log_dir.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Format for structured logging
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler (always output to console)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation (500MB files, keep 5 backups)
    log_file = log_dir / 'voicetv.log'
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=500 * 1024 * 1024,  # 500MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Error-only log file
    error_log_file = log_dir / 'voicetv_errors.log'
    error_handler = logging.handlers.RotatingFileHandler(
        filename=error_log_file,
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # Get logger for this module
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized at level {logging.getLevelName(log_level)}")
    logger.info(f"Log files location: {log_dir}")

    return logger


def get_logger(name):
    """
    Get a logger instance for a specific module

    Args:
        name: Module name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Pre-configure logging on import
logger = logging.getLogger(__name__)
