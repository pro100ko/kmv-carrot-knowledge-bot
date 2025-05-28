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
        # Log the update
        if isinstance(event, Update):
            if event.message:
                logger.info(f"Received message from user {event.message.from_user.id}: {event.message.text}")
            elif event.callback_query:
                logger.info(f"Received callback query from user {event.callback_query.from_user.id}: {event.callback_query.data}")
            else:
                logger.info(f"Received update: {event}")
        
        try:
            # Process the update
            return await handler(event, data)
        except Exception as e:
            # Log any errors
            logger.error(f"Error processing update: {e}", exc_info=True)
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
            if "message is not modified" in str(e):
                # Ignore "message is not modified" errors
                logger.debug(f"Ignoring 'message is not modified' error: {e}")
                return None
            elif "message to edit not found" in str(e):
                # Handle deleted messages
                logger.warning(f"Message to edit not found: {e}")
                return None
            else:
                # Log other Telegram errors
                logger.error(f"Telegram error: {e}", exc_info=True)
                raise
        except Exception as e:
            # Log other errors
            logger.error(f"Error in handler: {e}", exc_info=True)
            raise

# Register middlewares
dp.update.middleware(LoggingMiddleware())
dp.update.middleware(ErrorHandlerMiddleware())

# Global error handler
@dp.errors()
async def global_error_handler(update: Optional[Update], exception: Exception) -> bool:
    """Global error handler for all unhandled exceptions"""
    if isinstance(exception, TelegramBadRequest):
        if "message is not modified" in str(exception):
            return True
        elif "message to edit not found" in str(exception):
            return True
        elif "bot was blocked by the user" in str(exception):
            logger.warning(f"Bot was blocked by user: {update.message.from_user.id if update and update.message else 'unknown'}")
            return True
    
    # Log the error
    logger.error(
        f"Update {update} caused error {exception}",
        exc_info=True,
        extra={
            "update": update,
            "exception": exception
        }
    )
    
    # Try to notify the user if possible
    if update and update.message:
        try:
            await update.message.answer(
                "Произошла ошибка при обработке вашего запроса. "
                "Пожалуйста, попробуйте позже или обратитесь к администратору."
            )
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}", exc_info=True)
    
    return True

# Unhandled update handler
@dp.update()
async def unhandled_update_handler(update: Update) -> None:
    """Handle updates that don't match any registered handlers"""
    if update.message:
        logger.warning(f"Unhandled message from user {update.message.from_user.id}: {update.message.text}")
        try:
            await update.message.answer(
                "Извините, я не понял эту команду. "
                "Используйте /start для начала работы или /help для получения справки."
            )
        except Exception as e:
            logger.error(f"Failed to send help message: {e}", exc_info=True)
    elif update.callback_query:
        logger.warning(f"Unhandled callback query from user {update.callback_query.from_user.id}: {update.callback_query.data}")
        try:
            await update.callback_query.answer(
                "Эта кнопка больше не активна. Пожалуйста, обновите меню командой /start",
                show_alert=True
            )
        except Exception as e:
            logger.error(f"Failed to answer callback query: {e}", exc_info=True)
    else:
        logger.warning(f"Unhandled update: {update}")
