import time
import functools
from typing import Callable, Dict, Any, Optional, Union
from datetime import datetime

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, Update
from aiogram.dispatcher.flags import get_flag
from aiogram.exceptions import TelegramAPIError

from logging_config import app_logger, user_logger, admin_logger
from sqlite_db import db

class ErrorHandlingMiddleware(BaseMiddleware):
    """Middleware for handling errors in handlers"""
    
    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except TelegramAPIError as e:
            # Handle Telegram API errors
            error_msg = f"Telegram API error: {e}"
            app_logger.error(error_msg)
            
            # Try to notify user if possible
            if isinstance(event, (Message, CallbackQuery)):
                user_id = event.from_user.id
                try:
                    if isinstance(event, Message):
                        await event.answer(
                            "Произошла ошибка при обработке запроса. "
                            "Пожалуйста, попробуйте позже."
                        )
                    else:  # CallbackQuery
                        await event.answer(
                            "Произошла ошибка. Пожалуйста, попробуйте еще раз.",
                            show_alert=True
                        )
                except Exception as notify_error:
                    app_logger.error(f"Failed to notify user {user_id}: {notify_error}")
            
            return None
        except Exception as e:
            # Handle all other errors
            error_msg = f"Unexpected error in handler: {e}"
            app_logger.error(error_msg, exc_info=True)
            
            # Try to notify user if possible
            if isinstance(event, (Message, CallbackQuery)):
                user_id = event.from_user.id
                try:
                    if isinstance(event, Message):
                        await event.answer(
                            "Произошла непредвиденная ошибка. "
                            "Администратор уже уведомлен."
                        )
                    else:  # CallbackQuery
                        await event.answer(
                            "Произошла ошибка. Администратор уведомлен.",
                            show_alert=True
                        )
                except Exception as notify_error:
                    app_logger.error(f"Failed to notify user {user_id}: {notify_error}")
            
            return None

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

class StateManagementMiddleware(BaseMiddleware):
    """Middleware for managing user state"""
    
    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)
        
        user_id = event.from_user.id
        
        try:
            # Get current state
            state_data = db.get_user_state(user_id)
            current_state = state_data.get('state') if state_data else None
            
            # Update state data if needed
            if current_state:
                # Get state data from handler if available
                state_data = get_flag(data, "state_data")
                if state_data:
                    db.update_user_state(user_id, current_state, str(state_data))
            
            # Call handler
            result = await handler(event, data)
            
            # Update last active timestamp
            db.register_user({
                'telegram_id': user_id,
                'first_name': event.from_user.first_name,
                'last_name': event.from_user.last_name,
                'username': event.from_user.username
            })
            
            return result
        except Exception as e:
            app_logger.error(f"State management error for user {user_id}: {e}")
            return await handler(event, data)

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
            # Get current timestamp
            now = datetime.now().isoformat()
            
            # Update user activity
            db.register_user({
                'telegram_id': user_id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'last_active': now
            })
            
            # Log user activity
            if isinstance(event, Message):
                user_logger.info(
                    f"User {user_id} ({user.username or user.first_name}) "
                    f"sent message: {event.text[:100]}..."
                )
            else:  # CallbackQuery
                user_logger.info(
                    f"User {user_id} ({user.username or user.first_name}) "
                    f"pressed button: {event.data}"
                )
            
            return await handler(event, data)
            
        except Exception as e:
            user_logger.error(f"User activity tracking error for user {user_id}: {e}")
            return await handler(event, data)

def register_middlewares(dispatcher):
    """Register all middlewares with the dispatcher"""
    dispatcher.update.middleware(ErrorHandlingMiddleware())
    dispatcher.update.middleware(TimingMiddleware())
    dispatcher.update.middleware(StateManagementMiddleware())
    dispatcher.update.middleware(AdminAccessMiddleware())
    dispatcher.update.middleware(UserActivityMiddleware())
    
    app_logger.info("All middlewares registered successfully") 