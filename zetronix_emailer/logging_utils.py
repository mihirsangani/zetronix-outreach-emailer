"""Logging utility for the Zetronix Outreach Emailer."""

import logging
import sys
from pathlib import Path
from typing import Optional
from .config import config


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console logging."""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'ENDC': '\033[0m',      # End color
    }
    
    def format(self, record):
        """Format log record with colors."""
        log_color = self.COLORS.get(record.levelname, self.COLORS['ENDC'])
        reset = self.COLORS['ENDC']
        
        # Format the message
        formatted = super().format(record)
        return f"{log_color}{formatted}{reset}"


def setup_logger(
    name: str,
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    include_console: bool = True
) -> logging.Logger:
    """Set up a logger with file and console handlers.
    
    Args:
        name: Logger name
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Log file path
        include_console: Whether to include console handler
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Set log level
    level = getattr(logging, (log_level or config.log_level).upper())
    logger.setLevel(level)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File handler
    if log_file or config.log_file:
        file_path = Path(log_file or config.log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Console handler
    if include_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return setup_logger(name)


# Create main application logger
logger = get_logger("zetronix_emailer")