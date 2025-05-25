from aiogram import types
from aiogram.exceptions import TelegramBadRequest
from typing import Optional, Union
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class MessageEditor:
    """Класс для безопасной работы с сообщениями"""
    
    @staticmethod
    async def safe_edit(
        target: Union[types.Message, types.CallbackQuery],
        text: str,
        reply_markup: Optional[types.InlineKeyboardMarkup] = None,
        parse_mode: Optional[str] = None,
        disable_web_page_preview: bool = True,
        **kwargs
    ) -> bool:
        """
        Безопасное редактирование сообщения
        :param target: Сообщение или callback query
        :param text: Новый текст сообщения
        :param reply_markup: Новая клавиатура
        :param parse_mode: Режим парсинга (HTML/Markdown)
        :param disable_web_page_preview: Отключить превью ссылок
        :return: True если сообщение было изменено
        """
        try:
            if isinstance(target, types.CallbackQuery):
                message = target.message
                await target.answer()
            else:
                message = target
            
            # Проверяем необходимость изменений
            need_edit = (
                message.text != text or
                (message.reply_markup and reply_markup and 
                 message.reply_markup != reply_markup) or
                (reply_markup and not message.reply_markup)
            )
            
            if need_edit:
                await message.edit_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                    disable_web_page_preview=disable_web_page_preview,
                    **kwargs
                )
                return True
            return False
            
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                logger.error(f"Error editing message: {e}")
                raise
            return False
        except Exception as e:
            logger.error(f"Unexpected error in safe_edit: {e}")
            raise
    
    @staticmethod
    async def safe_send(
        target: Union[types.Message, types.CallbackQuery],
        text: str,
        reply_markup: Optional[Union[
            types.InlineKeyboardMarkup,
            types.ReplyKeyboardMarkup
        ]] = None,
        parse_mode: Optional[str] = None,
        **kwargs
    ) -> Optional[types.Message]:
        """
        Безопасная отправка сообщения
        :param target: Сообщение или callback query
        :param text: Текст сообщения
        :param reply_markup: Клавиатура
        :param parse_mode: Режим парсинга
        :return: Объект сообщения или None при ошибке
        """
        try:
            if isinstance(target, types.CallbackQuery):
                chat_id = target.message.chat.id
                await target.answer()
            else:
                chat_id = target.chat.id
            
            return await target.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return None
    
    @staticmethod
    async def safe_delete(
        message: types.Message,
        delay: Optional[float] = None
    ) -> bool:
        """
        Безопасное удаление сообщения
        :param message: Сообщение для удаления
        :param delay: Задержка перед удалением в секундах
        :return: True если сообщение было удалено
        """
        try:
            if delay:
                await asyncio.sleep(delay)
            await message.delete()
            return True
        except TelegramBadRequest as e:
            if "message to delete not found" not in str(e):
                logger.warning(f"Error deleting message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in safe_delete: {e}")
            return False

async def safe_edit_message(
    message: types.Message,
    text: str,
    reply_markup: Optional[types.InlineKeyboardMarkup] = None,
    **kwargs
) -> bool:
    """Совместимость со старой версией"""
    return await MessageEditor.safe_edit(
        message, text, reply_markup, **kwargs
    )

async def safe_send_message(
    target: Union[types.Message, types.CallbackQuery],
    text: str,
    reply_markup: Optional[Union[
        types.InlineKeyboardMarkup,
        types.ReplyKeyboardMarkup
    ]] = None,
    **kwargs
) -> Optional[types.Message]:
    """Совместимость со старой версией"""
    return await MessageEditor.safe_send(
        target, text, reply_markup, **kwargs
    )
