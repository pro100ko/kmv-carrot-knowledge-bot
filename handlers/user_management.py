import logging
from aiogram import types
from aiogram.enums import ParseMode
from typing import Optional, Union
from sqlite_db import (
    get_user,
    register_user,
    get_test_attempts,
    get_user_test_history,
    set_admin_status
)
from config import ADMIN_IDS
from utils.keyboards import get_main_keyboard
from utils.message_utils import safe_send_message

logger = logging.getLogger(__name__)

class UserManager:
    """Класс для управления пользователями"""
    
    @staticmethod
    async def register_or_update_user(user: types.User) -> bool:
        """Регистрирует или обновляет данные пользователя"""
        user_data = {
            'telegram_id': user.id,
            'first_name': user.first_name or '',
            'last_name': user.last_name or '',
            'username': user.username or '',
            'is_admin': user.id in ADMIN_IDS
        }
        
        try:
            return register_user(user_data)
        except Exception as e:
            logger.error(f"Failed to register user {user.id}: {e}")
            return False

    @staticmethod
    def is_admin(user_id: int) -> bool:
        """Проверяет, является ли пользователь администратором"""
        return user_id in ADMIN_IDS

async def start(
    update: Union[types.Message, types.CallbackQuery],
    context=None
) -> None:
    """Обработчик команды /start"""
    try:
        user = update.from_user
        is_admin = UserManager.is_admin(user.id)
        
        # Регистрируем/обновляем пользователя
        if not await UserManager.register_or_update_user(user):
            await handle_user_registration_error(update)
            return

        # Формируем приветственное сообщение
        welcome_message = (
            f"👋 Добро пожаловать в бот «Морковка КМВ», {user.first_name or 'пользователь'}!\n\n"
            "🥕 Здесь вы найдете:\n"
            "• Актуальную информацию о продуктах\n"
            "• Возможность проверить свои знания\n"
            "• Полезные материалы о нашей компании"
        )

        # Отправляем сообщение
        await safe_send_message(
            target=update,
            text=welcome_message,
            reply_markup=get_main_keyboard(is_admin)
        )

    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await handle_error(update)

async def register_user_handler(
    message: types.Message,
    context=None
) -> None:
    """Обработчик для регистрации пользователя и команд"""
    try:
        user = message.from_user
        is_admin = UserManager.is_admin(user.id)
        
        # Регистрируем/обновляем пользователя
        if not await UserManager.register_or_update_user(user):
            await handle_user_registration_error(message)
            return

        # Обрабатываем команды
        command = message.text.lower().strip()
        
        if command == "🍎 база знаний":
            from handlers.knowledge_base import knowledge_base_handler
            await knowledge_base_handler(message, context)
        elif command == "📝 тестирование":
            from handlers.testing import testing_handler
            await testing_handler(message, context)
        elif command == "⚙️ админ панель" and is_admin:
            from handlers.admin import admin_handler
            await admin_handler(message, context)
        else:
            await show_main_menu(message, is_admin)

    except Exception as e:
        logger.error(f"Error in register_user_handler: {e}")
        await handle_error(message)

async def show_main_menu(
    target: Union[types.Message, types.CallbackQuery],
    is_admin: bool = False
) -> None:
    """Показывает главное меню пользователя"""
    await safe_send_message(
        target=target,
        text="📌 Выберите действие из меню:",
        reply_markup=get_main_keyboard(is_admin)
    )

async def handle_user_registration_error(
    target: Union[types.Message, types.CallbackQuery]
) -> None:
    """Обработчик ошибок регистрации пользователя"""
    await safe_send_message(
        target=target,
        text="⚠️ Произошла ошибка при обработке вашего профиля. Пожалуйста, попробуйте позже."
    )

async def handle_error(
    target: Union[types.Message, types.CallbackQuery]
) -> None:
    """Обработчик ошибок"""
    await safe_send_message(
        target=target,
        text="⚠️ Произошла ошибка. Пожалуйста, попробуйте позже."
    )

async def get_user_profile(
    query: types.CallbackQuery,
    context=None
) -> None:
    """Показывает профиль пользователя и статистику"""
    try:
        user = query.from_user
        user_data = get_user(user.id)
        if not user_data:
            await query.answer("Профиль не найден")
            return

        # Формируем текст профиля
        profile_text = [
            f"👤 <b>Ваш профиль</b>",
            f"\n\n🆔 ID: {user.id}",
            f"\n👁‍🗨 Имя: {user_data.get('first_name', '')}",
            f"\n👥 Фамилия: {user_data.get('last_name', '')}",
            f"\n📱 Username: @{user_data.get('username', '')}" if user_data.get('username') else "",
            f"\n🎖 Статус: {'Администратор' if UserManager.is_admin(user.id) else 'Пользователь'}"
        ]

        # Добавляем статистику тестов
        attempts = get_test_attempts(user.id)
        if attempts:
            passed = sum(1 for a in attempts if a['score'] / a['max_score'] >= 0.7)
            profile_text.extend([
                f"\n\n📊 <b>Статистика тестов</b>",
                f"\n✅ Пройдено: {passed}/{len(attempts)}",
                f"\n🏆 Лучший результат: {max(a['score'] for a in attempts)}/{attempts[0]['max_score']}"
            ])

        await safe_edit_message(
            message=query.message,
            text="".join(profile_text),
            parse_mode=ParseMode.HTML,
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data="main_menu"
                )
            ]])
        )
        await query.answer()

    except Exception as e:
        logger.error(f"Error in get_user_profile: {e}")
        await handle_error(query)
