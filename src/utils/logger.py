"""
Logger Utility for YamiBot

This module provides centralized logging functionality for the bot.
"""

import logging
import os
import psutil
import time
from datetime import datetime
from typing import Optional

# Configure logging format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

class CustomFormatter(logging.Formatter):
    """
    Custom log formatter that adds color to console output
    """
    
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: grey + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset
    }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt=LOG_DATE_FORMAT)
        return formatter.format(record)

def setup_logging(name: str, log_level: Optional[int] = None) -> logging.Logger:
    """
    Setup and configure logging for a module
    
    Args:
        name: Module name for the logger
        log_level: Optional log level override
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    
    # Set log level (default to INFO if not specified)
    if log_level is None:
        log_level = logging.INFO
    
    logger.setLevel(log_level)
    
    # Prevent duplicate handlers
    if logger.hasHandlers():
        return logger
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(CustomFormatter())
    
    # Create file handler
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d")
    log_filename = f"{log_dir}/yamibot_{timestamp}.log"
    
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Setup root logger
def setup_root_logging():
    """
    Setup root logging configuration
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Add console handler to root logger
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(CustomFormatter())
    
    root_logger.addHandler(console_handler)
    
    return root_logger

def log_memory_status():
    """
    Log current memory usage of the process
    
    Returns:
        Dictionary with memory usage information
    """
    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        memory_mb = memory_info.rss / 1024 / 1024
        virtual_mb = memory_info.vms / 1024 / 1024
        
        logger.info(
            f"Memory usage: {memory_mb:.2f}MB "
            f"(Virtual: {virtual_mb:.2f}MB)"
        )
        
        return {
            "rss_mb": round(memory_mb, 2),
            "vms_mb": round(virtual_mb, 2),
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Error getting memory status: {e}")
        return {
            "rss_mb": 0,
            "vms_mb": 0,
            "timestamp": time.time(),
            "error": str(e)
        }