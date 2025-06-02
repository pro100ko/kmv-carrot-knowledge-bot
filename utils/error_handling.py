"""Error handling utilities for the bot."""

from typing import Optional, Dict, Any
import logging
from functools import wraps
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest

logger = logging.getLogger(__name__)

class BotError(Exception):
    """Base exception for bot errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class DatabaseError(BotError):
    """Database operation error."""
    pass

class UserError(BotError):
    """User-related error."""
    pass

class AdminError(BotError):
    """Admin operation error."""
    pass

class TestError(BotError):
    """Test-related error."""
    pass

class ValidationError(BotError):
    """Data validation error."""
    pass

class StateError(BotError):
    """State management error."""
    pass

def handle_errors(func):
    """Decorator for handling errors in handlers."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except TelegramAPIError as e:
            logger.error(f"Telegram API error in {func.__name__}: {e}")
            # Handle rate limits and other Telegram-specific errors
            if "Too Many Requests" in str(e):
                raise BotError("Too many requests. Please try again later.")
            raise BotError(f"Telegram API error: {e}")
        except DatabaseError as e:
            logger.error(f"Database error in {func.__name__}: {e}")
            raise BotError("Database operation failed. Please try again later.")
        except ValidationError as e:
            logger.warning(f"Validation error in {func.__name__}: {e}")
            raise BotError(str(e))
        except StateError as e:
            logger.warning(f"State error in {func.__name__}: {e}")
            raise BotError("Session expired. Please start over.")
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            raise BotError("An unexpected error occurred. Please try again later.")
    return wrapper

def log_operation(operation_name: str):
    """Decorator for logging operations."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger.info(f"Starting {operation_name} in {func.__name__}")
            try:
                result = await func(*args, **kwargs)
                logger.info(f"Completed {operation_name} in {func.__name__}")
                return result
            except Exception as e:
                logger.error(f"Failed {operation_name} in {func.__name__}: {e}")
                raise
        return wrapper
    return decorator

def validate_state(state_name: str):
    """Decorator for validating handler state."""
    def decorator(func):
        @wraps(func)
        async def wrapper(event, state, *args, **kwargs):
            current_state = await state.get_state()
            if current_state != state_name:
                logger.warning(
                    f"Invalid state in {func.__name__}: "
                    f"expected {state_name}, got {current_state}"
                )
                raise StateError(f"Invalid state: expected {state_name}")
            return await func(event, state, *args, **kwargs)
        return wrapper
    return decorator 