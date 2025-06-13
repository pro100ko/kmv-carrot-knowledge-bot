import time
import functools
from typing import Callable, Dict, Any, Optional, Union, Awaitable
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, Update
from aiogram.dispatcher.flags import get_flag
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest

from logging_config import app_logger, user_logger, admin_logger
from sqlite_db import db
from config import get_config
from monitoring.metrics import metrics_collector
from utils.error_handling import handle_errors, log_operation, validate_state

logger = logging.getLogger(__name__)

def get_handler_name(handler: Callable) -> str:
    """Safely get handler name, handling functools.partial objects."""
    if isinstance(handler, functools.partial):
        # For partial objects, try to get the name of the wrapped function
        if hasattr(handler.func, '__name__'):
            return handler.func.__name__
        return 'partial_handler'
    return getattr(handler, '__name__', 'unknown_handler')

class MetricsMiddleware(BaseMiddleware):
    """Middleware for collecting metrics."""
    def __init__(self):
        self.config = get_config()
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Process event and collect metrics."""
        # Only collect metrics if enabled in config
        if not self.config.ENABLE_METRICS:
            return await handler(event, data)

        start_time = time.time()
        
        try:
            # Record event type
            if isinstance(event, Message):
                metrics_collector.increment_message_count()
                handler_name = "message_handler"
            elif isinstance(event, CallbackQuery):
                metrics_collector.increment_callback_count()
                handler_name = "callback_handler"
            else:
                handler_name = "unknown_handler"
            
            # Process event
            result = await handler(event, data)
            
            # Record success metrics
            duration = time.time() - start_time
            metrics_collector.record_handler_operation(
                handler=handler_name,
                operation=get_handler_name(handler),
                duration=duration
            )
            metrics_collector.record_request_time(duration)
            
            return result
            
        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time
            metrics_collector.increment_error_count(str(type(e).__name__))
            metrics_collector.record_handler_operation(
                handler=handler_name,
                operation=get_handler_name(handler),
                duration=duration,
                error=str(e)
            )
            raise

class ErrorHandlingMiddleware(BaseMiddleware):
    """Middleware for handling errors."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Process event with error handling."""
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Error in handler {get_handler_name(handler)}: {e}", exc_info=True)
            metrics_collector.increment_error_count(str(type(e).__name__))
            
            # Try to send error message to user
            try:
                if isinstance(event, Message):
                    await event.answer(
                        "Произошла ошибка при обработке запроса. "
                        "Пожалуйста, попробуйте позже или обратитесь к администратору."
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "Произошла ошибка. Попробуйте еще раз.",
                        show_alert=True
                    )
            except Exception as send_error:
                logger.error(f"Error sending error message: {send_error}")
            
            raise

class StateManagementMiddleware(BaseMiddleware):
    """Middleware for managing user state."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Process event with state management."""
        start_time = time.time()
        
        try:
            # Get user state
            state = data.get("state")
            if state:
                # Record state operation
                metrics_collector.record_operation(
                    operation="state_management",
                    duration=time.time() - start_time
                )
            
            return await handler(event, data)
            
        except Exception as e:
            # Record state error
            duration = time.time() - start_time
            metrics_collector.record_operation(
                operation="state_management",
                duration=duration,
                error=str(e)
            )
            raise

class LoggingMiddleware(BaseMiddleware):
    """Middleware for logging."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Process event with logging."""
        start_time = time.time()
        
        try:
            # Log event
            if isinstance(event, Message):
                logger.info(
                    f"Processing message from user {event.from_user.id}: "
                    f"{event.text or '[non-text message]'}"
                )
            elif isinstance(event, CallbackQuery):
                logger.info(
                    f"Processing callback from user {event.from_user.id}: "
                    f"{event.data}"
                )
            
            # Process event
            result = await handler(event, data)
            
            # Record logging operation
            duration = time.time() - start_time
            metrics_collector.record_operation(
                operation=get_handler_name(handler),
                duration=duration
            )
            
            return result
            
        except Exception as e:
            # Record logging error
            duration = time.time() - start_time
            metrics_collector.record_operation(
                operation=get_handler_name(handler),
                duration=duration,
                error=str(e)
            )
            raise

class TimingMiddleware(BaseMiddleware):
    """Middleware for measuring handler execution time"""
    
    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Process event and measure execution time."""
        start_time = time.time()
        try:
            return await handler(event, data)
        finally:
            end_time = time.time()
            duration = end_time - start_time
            handler_name = get_handler_name(handler)
            logger.debug(f"Handler '{handler_name}' executed in {duration:.4f} seconds")
            metrics_collector.record_operation(operation=f"handler_execution_{handler_name}", duration=duration)

class AdminAccessMiddleware(BaseMiddleware):
    """Middleware for checking admin access."""

    def __init__(self):
        self.config = get_config()
        super().__init__()

    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Process event with admin access check."""
        # Check if handler requires admin access
        if get_flag(handler, "admin_only"):
            user_id = event.from_user.id
            if user_id not in self.config.ADMIN_IDS: # Use self.config.ADMIN_IDS
                logger.warning(f"User {user_id} attempted to access admin-only handler {get_handler_name(handler)}")
                if isinstance(event, Message):
                    await event.answer("У вас нет прав для выполнения этой команды.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("У вас нет прав для выполнения этой команды.", show_alert=True)
                return # Block access
        
        return await handler(event, data)

class UserActivityMiddleware(BaseMiddleware):
    """Middleware for logging user activity."""

    def __init__(self):
        super().__init__()

    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Process event and log user activity."""
        # We need the user service from the context, which is set in main.py::on_startup
        user_service = data.get("user_service")
        if not user_service:
            logger.error("UserService not found in middleware data.")
            return await handler(event, data) # Continue without logging activity

        user = event.from_user
        action = None
        details = None

        if isinstance(event, Message):
            action = "message"
            details = f"Text: {event.text}"
        elif isinstance(event, CallbackQuery):
            action = "callback_query"
            details = f"Data: {event.data}"
        elif isinstance(event, Update):
            # This might be too broad, consider specific update types if needed
            action = "update"
            details = f"Update ID: {event.update_id}"
        
        if user and action:
            # Log activity in a non-blocking way if possible, or update last activity
            # For now, let's update last activity directly for simplicity
            try:
                await user_service.update_last_activity(user.id) # Assuming user.id is Telegram ID
                # If you need detailed logging, you'd call a specific log_activity method here
            except Exception as e:
                logger.error(f"Error updating user last activity for {user.id}: {e}")

        return await handler(event, data)

class RateLimitMiddleware(BaseMiddleware):
    """Middleware for rate limiting messages and callbacks."""
    
    def __init__(self):
        self.config = get_config()
        self.message_timestamps = defaultdict(list)
        self.callback_timestamps = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Any],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        current_time = time.time()
        
        if isinstance(event, Message):
            timestamps = self.message_timestamps[user_id]
            rate_limit = self.config.RATE_LIMIT_MESSAGES
            window = self.config.RATE_LIMIT_WINDOW
        elif isinstance(event, CallbackQuery):
            timestamps = self.callback_timestamps[user_id]
            rate_limit = self.config.RATE_LIMIT_CALLBACKS
            window = self.config.RATE_LIMIT_WINDOW
        else:
            return await handler(event, data) # Not a message or callback, skip rate limit

        # Clean up old timestamps
        timestamps[:] = [t for t in timestamps if current_time - t < window]

        if len(timestamps) >= rate_limit:
            logger.warning(f"User {user_id} hit rate limit for {type(event).__name__}")
            if isinstance(event, Message):
                await event.answer(
                    "Слишком много запросов. Пожалуйста, подождите немного и попробуйте снова."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "Слишком много запросов. Пожалуйста, подождите немного и попробуйте снова.",
                    show_alert=True
                )
            return # Block event
        
        timestamps.append(current_time)
        return await handler(event, data)

def register_middlewares(dispatcher):
    """Register all application-specific middlewares with the dispatcher."""
    dispatcher.update.middleware(MetricsMiddleware())
    dispatcher.update.middleware(ErrorHandlingMiddleware())
    dispatcher.update.middleware(StateManagementMiddleware())
    dispatcher.update.middleware(LoggingMiddleware())
    dispatcher.update.middleware(AdminAccessMiddleware())
    dispatcher.update.middleware(UserActivityMiddleware())
    dispatcher.update.middleware(RateLimitMiddleware())

# Create middleware instances
metrics_middleware = MetricsMiddleware()
error_handling_middleware = ErrorHandlingMiddleware()
state_management_middleware = StateManagementMiddleware()
logging_middleware = LoggingMiddleware() 