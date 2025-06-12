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
from config import (
    RATE_LIMIT_MESSAGES,
    RATE_LIMIT_CALLBACKS,
    RATE_LIMIT_WINDOW,
    ENABLE_METRICS
)
from monitoring.metrics import metrics_collector
from utils.error_handling import handle_errors, log_operation, validate_state

logger = logging.getLogger(__name__)

class MetricsMiddleware(BaseMiddleware):
    """Middleware for collecting metrics."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Process event and collect metrics."""
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
                operation=handler.__name__,
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
                operation=handler.__name__,
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
            logger.error(f"Error in handler {handler.__name__}: {e}", exc_info=True)
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
                operation="logging",
                duration=duration
            )
            
            return result
            
        except Exception as e:
            # Record logging error
            duration = time.time() - start_time
            metrics_collector.record_operation(
                operation="logging",
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
        start_time = time.time()
        
        try:
            return await handler(event, data)
        finally:
            execution_time = time.time() - start_time
            
            # Get handler name
            handler_name = handler.__name__
            
            # Get user info if available
            user_info = ""
            if isinstance(event, (Message, CallbackQuery)):
                user = event.from_user
                user_info = f" (user: {user.id}, {user.username or user.first_name})"
            
            # Log timing information
            if execution_time > 1.0:  # Log slow handlers
                app_logger.warning(
                    f"Slow handler: {handler_name}{user_info} "
                    f"took {execution_time:.2f} seconds"
                )
            else:
                app_logger.debug(
                    f"Handler: {handler_name}{user_info} "
                    f"took {execution_time:.2f} seconds"
                )

class AdminAccessMiddleware(BaseMiddleware):
    """Middleware for checking admin access"""
    
    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)
        
        user_id = event.from_user.id
        
        # Check if handler requires admin access
        requires_admin = get_flag(data, "requires_admin", False)
        if not requires_admin:
            return await handler(event, data)
        
        try:
            # Check if user is admin
            user = db.get_user(user_id)
            if not user or not user.get('is_admin'):
                admin_logger.warning(
                    f"Unauthorized admin access attempt by user {user_id} "
                    f"({event.from_user.username or event.from_user.first_name})"
                )
                
                if isinstance(event, Message):
                    await event.answer(
                        "У вас нет доступа к этой команде. "
                        "Требуются права администратора."
                    )
                else:  # CallbackQuery
                    await event.answer(
                        "Требуются права администратора.",
                        show_alert=True
                    )
                return None
            
            # User is admin, proceed with handler
            admin_logger.info(
                f"Admin access granted to user {user_id} "
                f"({event.from_user.username or event.from_user.first_name})"
            )
            return await handler(event, data)
            
        except Exception as e:
            admin_logger.error(f"Admin access check error for user {user_id}: {e}")
            return None

class UserActivityMiddleware(BaseMiddleware):
    """Middleware for tracking user activity"""
    
    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)
        
        user_id = event.from_user.id
        user = event.from_user
        
        try:
            # Get database pool from storage
            storage_data = await data['dispatcher'].storage.get_data(key=STORAGE_KEYS['db_pool'])
            if not storage_data or 'db_pool' not in storage_data:
                logger.error("Database pool not found in storage")
                return await handler(event, data)
            
            # Get current timestamp
            now = datetime.now().isoformat()
            
            # Update user activity asynchronously
            try:
                # Get user from database first
                user_data = await sqlite_db.db.get_user(user_id)
                if not user_data:
                    # Register new user if not exists
                    await sqlite_db.db.register_user({
                        'telegram_id': user_id,
                        'username': user.username,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'role': UserRole.ADMIN.value if user_id in ADMIN_IDS else UserRole.USER.value,
                        'last_active': now
                    })
                    logger.info(f"Registered new user {user_id} in middleware")
                else:
                    # Update existing user's activity
                    await sqlite_db.db.register_user({
                        'telegram_id': user_id,
                        'last_active': now
                    })
                    logger.debug(f"Updated activity for user {user_id}")
            except Exception as db_error:
                logger.error(f"Failed to update user activity in middleware: {db_error}", exc_info=True)
                # Continue processing even if activity update fails
            
            # Log user activity
            if isinstance(event, Message):
                logger.info(
                    f"User {user_id} ({user.username or user.first_name}) "
                    f"sent message: {event.text[:100] if event.text else 'non-text message'}..."
                )
            else:  # CallbackQuery
                logger.info(
                    f"User {user_id} ({user.username or user.first_name}) "
                    f"pressed button: {event.data}"
                )
            
            # Continue with handler
            return await handler(event, data)
            
        except Exception as e:
            logger.error(f"User activity middleware error for user {user_id}: {e}", exc_info=True)
            # Continue with handler even if middleware fails
            return await handler(event, data)

class RateLimitMiddleware(BaseMiddleware):
    """Middleware to handle rate limiting"""
    
    def __init__(self):
        """Initialize rate limiter"""
        super().__init__()
        self._message_limits: Dict[int, list] = defaultdict(list)  # user_id -> timestamps
        self._callback_limits: Dict[int, list] = defaultdict(list)  # user_id -> timestamps
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Any],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Process update with rate limiting"""
        # Get user ID
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
            limits = self._message_limits
            max_requests = RATE_LIMIT_MESSAGES
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            limits = self._callback_limits
            max_requests = RATE_LIMIT_CALLBACKS
        else:
            return await handler(event, data)
        
        if not user_id:
            return await handler(event, data)
        
        # Check rate limit
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW
        
        # Clean up old timestamps
        limits[user_id] = [ts for ts in limits[user_id] if ts > window_start]
        
        # Check if limit exceeded
        if len(limits[user_id]) >= max_requests:
            if ENABLE_METRICS:
                metrics_collector.record_error("rate_limit")
            
            if isinstance(event, Message):
                try:
                    await event.answer(
                        "Слишком много сообщений. Пожалуйста, подождите немного."
                    )
                except TelegramBadRequest as e:
                    app_logger.warning(f"Could not send rate limit message: {e}")
            elif isinstance(event, CallbackQuery):
                try:
                    await event.answer(
                        "Слишком много запросов. Пожалуйста, подождите немного.",
                        show_alert=True
                    )
                except TelegramBadRequest as e:
                    app_logger.warning(f"Could not send rate limit callback: {e}")
            
            return
        
        # Record request
        limits[user_id].append(now)
        
        # Process update
        try:
            return await handler(event, data)
        except Exception as e:
            if ENABLE_METRICS:
                metrics_collector.record_error("other")
            raise

def register_middlewares(dispatcher):
    """Register all middlewares with the dispatcher"""
    dispatcher.update.middleware(ErrorHandlingMiddleware())
    dispatcher.update.middleware(TimingMiddleware())
    dispatcher.update.middleware(StateManagementMiddleware())
    dispatcher.update.middleware(AdminAccessMiddleware())
    dispatcher.update.middleware(UserActivityMiddleware())
    dispatcher.update.middleware(RateLimitMiddleware())
    dispatcher.update.middleware(LoggingMiddleware())
    
    app_logger.info("All middlewares registered successfully")

# Create middleware instances
metrics_middleware = MetricsMiddleware()
error_handling_middleware = ErrorHandlingMiddleware()
state_management_middleware = StateManagementMiddleware()
logging_middleware = LoggingMiddleware() 