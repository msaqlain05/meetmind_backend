"""Centralized logging configuration"""

import logging
import sys
from app.config import settings


def setup_logger(name: str) -> logging.Logger:
    """
    Setup logger with consistent formatting.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set level based on debug mode
    logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Formatter with timestamp, name, level, and message
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger
