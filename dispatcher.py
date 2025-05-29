# dispatcher.py
import logging
from typing import Optional, Any, Dict, Callable, Awaitable

from aiogram import BaseMiddleware, Dispatcher
from aiogram.types import TelegramObject, Update, Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.memory import MemoryStorage

# Create logger
logger = logging.getLogger(__name__)

# Initialize dispatcher with memory storage
dp = Dispatcher(storage=MemoryStorage())

class LoggingMiddleware(BaseMiddleware):
    """Middleware to log all updates"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Log the update with more details
        if isinstance(event, Update):
            if event.message:
                logger.info(
                    f"Received message from user {event.message.from_user.id}: "
                    f"text='{event.message.text}', "
                    f"message_id={event.message.message_id}"
                )
            elif event.callback_query:
                logger.info(
                    f"Received callback query from user {event.callback_query.from_user.id}: "
                    f"data='{event.callback_query.data}', "
                    f"message_id={event.callback_query.message.message_id if event.callback_query.message else 'N/A'}"
                )
            else:
                logger.info(f"Received update: {event}")
        
        try:
            # Process the update
            result = await handler(event, data)
            logger.debug(f"Handler {handler.__name__} completed successfully")
            return result
        except Exception as e:
            # Log any errors with full context
            logger.error(
                f"Error in handler {handler.__name__}: {e}",
                exc_info=True,
                extra={
                    "handler": handler.__name__,
                    "event": event,
                    "error": str(e)
                }
            )
            raise

class ErrorHandlerMiddleware(BaseMiddleware):
    """Middleware to handle common errors"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except TelegramBadRequest as e:
            error_msg = str(e)
            if "message is not modified" in error_msg:
                logger.debug(f"Ignoring 'message is not modified' error: {e}")
                return None
            elif "message to edit not found" in error_msg:
                logger.warning(f"Message to edit not found: {e}")
                return None
            elif "bot was blocked by the user" in error_msg:
                user_id = event.message.from_user.id if hasattr(event, 'message') else 'unknown'
                logger.warning(f"Bot was blocked by user {user_id}")
                return None
            else:
                logger.error(f"Telegram error in {handler.__name__}: {e}", exc_info=True)
                raise
        except Exception as e:
            logger.error(
                f"Error in handler {handler.__name__}: {e}",
                exc_info=True,
                extra={
                    "handler": handler.__name__,
                    "event": event,
                    "error": str(e)
                }
            )
            raise

# Register middlewares
dp.update.middleware(LoggingMiddleware())
dp.update.middleware(ErrorHandlerMiddleware())

# Global error handler
@dp.errors()
async def errors_handler(event: TelegramObject, exception: Exception) -> bool:
    """Global error handler with detailed logging"""
    try:
        # Get update details
        update_type = type(event).__name__
        user_id = event.from_user.id if hasattr(event, 'from_user') else 'unknown'
        message_id = event.message.message_id if hasattr(event, 'message') else 'unknown'
        callback_data = event.callback_query.data if hasattr(event, 'callback_query') else 'unknown'
        
        # Log the error with full context
        logger.error(
            f"Update caused error: {exception}",
            exc_info=True,
            extra={
                "update_type": update_type,
                "user_id": user_id,
                "message_id": message_id,
                "callback_data": callback_data,
                "exception_type": type(exception).__name__,
                "exception_args": getattr(exception, 'args', None)
            }
        )
        
        # Try to notify the user
        if hasattr(event, 'message'):
            await event.message.answer(
                "⚠️ Произошла ошибка при обработке вашего запроса.\n"
                "Пожалуйста, попробуйте позже или обратитесь к администратору."
            )
        elif hasattr(event, 'callback_query'):
            await event.callback_query.answer(
                "⚠️ Произошла ошибка. Пожалуйста, попробуйте позже.",
                show_alert=True
            )
    except Exception as e:
        logger.error(f"Error in error handler: {e}", exc_info=True)
    
    return True

# Unhandled update handler
@dp.update()
async def unhandled_update_handler(update: Update) -> None:
    """Handle updates that don't match any registered handlers"""
    if update.message:
        logger.warning(
            f"Unhandled message from user {update.message.from_user.id}: "
            f"text='{update.message.text}', "
            f"message_id={update.message.message_id}"
        )
        try:
            await update.message.answer(
                "⚠️ Извините, я не понял эту команду.\n"
                "Используйте /start для начала работы или /help для получения справки."
            )
        except Exception as e:
            logger.error(f"Failed to send help message: {e}", exc_info=True)
    elif update.callback_query:
        logger.warning(
            f"Unhandled callback query from user {update.callback_query.from_user.id}: "
            f"data='{update.callback_query.data}', "
            f"message_id={update.callback_query.message.message_id if update.callback_query.message else 'N/A'}"
        )
        try:
            await update.callback_query.answer(
                "⚠️ Эта кнопка больше не активна.\n"
                "Пожалуйста, обновите меню командой /start",
                show_alert=True
            )
        except Exception as e:
            logger.error(f"Failed to answer callback query: {e}", exc_info=True)
    else:
        logger.warning(f"Unhandled update: {update}")
