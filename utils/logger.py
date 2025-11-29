"""
Centralized logging configuration for AGI-Sentinel.
Provides structured logging with rotation and environment-specific settings.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional
import json
from datetime import datetime


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


def setup_logging(
    level: str = "INFO",
    log_dir: Optional[str] = None,
    json_format: bool = False,
    console: bool = True
) -> logging.Logger:
    """
    Configure logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (None = no file logging)
        json_format: Use JSON formatting for logs
        console: Enable console logging
        
    Returns:
        Configured root logger
    """
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create formatter
    if json_format:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Main log file with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_path / "agi_sentinel.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Error log file
        error_handler = logging.handlers.RotatingFileHandler(
            log_path / "errors.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: str, message: str, **context):
    """
    Log a message with additional context fields.
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **context: Additional context fields
    """
    log_func = getattr(logger, level.lower())
    
    # Create a log record with extra fields
    extra = {'extra_fields': context}
    log_func(message, extra=extra)


# Initialize default logging on module import
# Can be reconfigured by calling setup_logging()
_default_level = os.getenv("LOG_LEVEL", "INFO")
_default_log_dir = os.getenv("LOG_DIR", "./logs")
_use_json = os.getenv("LOG_JSON", "false").lower() == "true"

setup_logging(
    level=_default_level,
    log_dir=_default_log_dir,
    json_format=_use_json,
    console=True
)
