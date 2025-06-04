"""Utility functions for message handling"""

from typing import Optional, Union, Dict, Any
from aiogram import types, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging

from config import MAX_MESSAGE_LENGTH, MAX_CAPTION_LENGTH

# Configure logging
logger = logging.getLogger(__name__)

def truncate_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> str:
    """Truncate message text to maximum length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

def format_error_message(error: Union[str, Exception]) -> str:
    """Format error message for user display"""
    error_text = str(error)
    return f"⚠️ <b>Ошибка:</b>\n{error_text}"

def format_admin_message(title: str, content: str) -> str:
    """Format message for admin panel"""
    return f"👨‍💼 <b>{title}</b>\n\n{content}"

def format_user_message(user: Dict[str, Any]) -> str:
    """Format user information message"""
    return (
        f"👤 <b>Пользователь:</b> {user['name']}\n"
        f"🆔 Telegram ID: {user['telegram_id']}\n"
        f"👥 Роль: {user.get('role', 'user')}\n"
        f"📅 Регистрация: {user['created_at']}\n"
        f"🔄 Последняя активность: {user.get('last_active', 'Нет данных')}\n"
        f"📊 Статус: {'✅ Активен' if user['is_active'] else '❌ Неактивен'}"
    )

async def safe_send_message(
    chat_id: int,
    text: str,
    bot: Bot,
    parse_mode: Optional[str] = "HTML",
    reply_markup: Optional[types.InlineKeyboardMarkup] = None,
    **kwargs: Any
) -> Optional[types.Message]:
    """Safely send message with error handling"""
    try:
        # Truncate message if needed
        text = truncate_message(text)
        
        # Send message
        return await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            **kwargs
        )
    except TelegramBadRequest as e:
        if "message is too long" in str(e).lower():
            # Try to send truncated message
            try:
                return await bot.send_message(
                    chat_id=chat_id,
                    text=truncate_message(text, max_length=MAX_MESSAGE_LENGTH - 100) + "\n\n...",
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                    **kwargs
                )
            except Exception as e2:
                logger.error(f"Failed to send truncated message: {e2}")
        else:
            logger.error(f"Failed to send message: {e}")
    except Exception as e:
        logger.error(f"Unexpected error sending message: {e}")
    return None

async def safe_edit_message(
    message: types.Message,
    text: str,
    reply_markup: Optional[types.InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = "HTML",
    **kwargs: Any
) -> bool:
    """Safely edit message with error handling"""
    try:
        # Truncate message if needed
        text = truncate_message(text)
        
        # Edit message
        await message.edit_text(
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            **kwargs
        )
        return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            # Message content hasn't changed, this is not an error
            return True
        elif "message is too long" in str(e).lower():
            # Try to edit with truncated message
            try:
                await message.edit_text(
                    text=truncate_message(text, max_length=MAX_MESSAGE_LENGTH - 100) + "\n\n...",
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                    **kwargs
                )
                return True
            except Exception as e2:
                logger.error(f"Failed to edit with truncated message: {e2}")
        else:
            logger.error(f"Failed to edit message: {e}")
    except Exception as e:
        logger.error(f"Unexpected error editing message: {e}")
    return False

async def safe_delete_message(message: types.Message) -> bool:
    """Safely delete message with error handling"""
    try:
        await message.delete()
        return True
    except TelegramBadRequest as e:
        if "message to delete not found" in str(e).lower():
            # Message already deleted, this is not an error
            return True
        logger.error(f"Failed to delete message: {e}")
    except Exception as e:
        logger.error(f"Unexpected error deleting message: {e}")
    return False

async def safe_edit_caption(
    message: types.Message,
    caption: str,
    reply_markup: Optional[types.InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = "HTML",
    **kwargs: Any
) -> bool:
    """Safely edit message caption with error handling"""
    try:
        # Truncate caption if needed
        caption = truncate_message(caption, max_length=MAX_CAPTION_LENGTH)
        
        # Edit caption
        await message.edit_caption(
            caption=caption,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            **kwargs
        )
        return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            # Caption hasn't changed, this is not an error
            return True
        elif "caption is too long" in str(e).lower():
            # Try to edit with truncated caption
            try:
                await message.edit_caption(
                    caption=truncate_message(caption, max_length=MAX_CAPTION_LENGTH - 100) + "\n\n...",
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                    **kwargs
                )
                return True
            except Exception as e2:
                logger.error(f"Failed to edit with truncated caption: {e2}")
        else:
            logger.error(f"Failed to edit caption: {e}")
    except Exception as e:
        logger.error(f"Unexpected error editing caption: {e}")
    return False

def get_confirmation_keyboard(
    confirm_callback: str,
    cancel_callback: str,
    confirm_text: str = "✅ Да",
    cancel_text: str = "❌ Нет"
) -> types.InlineKeyboardMarkup:
    """Create confirmation keyboard"""
    builder = InlineKeyboardBuilder()
    builder.button(text=confirm_text, callback_data=confirm_callback)
    builder.button(text=cancel_text, callback_data=cancel_callback)
    builder.adjust(2)  # Two buttons in one row
    return builder.as_markup()

def get_back_keyboard(
    back_callback: str,
    back_text: str = "◀️ Назад"
) -> types.InlineKeyboardMarkup:
    """Create back button keyboard"""
    builder = InlineKeyboardBuilder()
    builder.button(text=back_text, callback_data=back_callback)
    builder.adjust(1)  # One button per row
    return builder.as_markup()
