import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional
from logging.handlers import RotatingFileHandler

# Constants
LOG_DIR = "logs"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_BYTES = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5

def setup_logging() -> None:
    """Setup logging configuration for the application"""
    # Create logs directory if it doesn't exist
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Generate log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(LOG_DIR, f"bot_{timestamp}.log")
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    root_logger.handlers = []
    
    # Create formatters
    file_formatter = logging.Formatter(LOG_FORMAT)
    console_formatter = logging.Formatter("%(levelname)s - %(message)s")
    
    # Create and configure file handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)
    
    # Create and configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Set logging level for specific modules
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # Log initial message
    logging.info("Logging system initialized")

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name"""
    return logging.getLogger(name)

def cleanup_old_logs() -> None:
    """Clean up old log files keeping only the last N backups"""
    try:
        # Get list of log files
        log_files = []
        for filename in os.listdir(LOG_DIR):
            if filename.startswith("bot_") and filename.endswith(".log"):
                filepath = os.path.join(LOG_DIR, filename)
                try:
                    # Get file creation time
                    timestamp = datetime.strptime(
                        filename[4:-4],  # Remove 'bot_' prefix and '.log' suffix
                        "%Y%m%d"
                    )
                    log_files.append({
                        'filename': filename,
                        'path': filepath,
                        'created_at': timestamp
                    })
                except ValueError:
                    continue
        
        # Sort by creation time
        log_files.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Remove old files
        for log_file in log_files[BACKUP_COUNT:]:
            try:
                os.remove(log_file['path'])
                logging.info(f"Removed old log file: {log_file['filename']}")
            except Exception as e:
                logging.error(f"Failed to remove log file {log_file['filename']}: {e}")
    
    except Exception as e:
        logging.error(f"Failed to cleanup old logs: {e}")

# Create default logger for the application
app_logger = get_logger("morkovka_bot")

# Create separate logger for database operations
db_logger = get_logger("morkovka_bot.db")

# Create separate logger for webhook operations
webhook_logger = get_logger("morkovka_bot.webhook")

# Create separate logger for admin operations
admin_logger = get_logger("morkovka_bot.admin")

# Create separate logger for user operations
user_logger = get_logger("morkovka_bot.user")

if __name__ == "__main__":
    # Test logging configuration
    setup_logging()
    
    # Test logging
    logger = get_logger(__name__)
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Test log cleanup
    cleanup_old_logs() 