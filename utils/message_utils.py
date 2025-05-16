from aiogram import types
from aiogram.exceptions import TelegramBadRequest

async def safe_edit_message(
    message: types.Message,
    text: str,
    reply_markup: types.InlineKeyboardMarkup = None
) -> bool:
    """
    Безопасное редактирование сообщения с проверкой изменений
    Возвращает True если редактирование было выполнено
    """
    try:
        if (message.text != text or 
            (message.reply_markup and reply_markup and 
             message.reply_markup != reply_markup)):
            await message.edit_text(
                text=text,
                reply_markup=reply_markup
            )
            return True
        return False
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise  # Пробрасываем другие ошибки
        return False
