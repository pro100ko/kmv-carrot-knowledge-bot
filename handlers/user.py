"""User management handlers for the bot."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlite_db import db, UserRole
from utils.keyboards import (
    get_main_menu_keyboard,
    get_admin_menu_keyboard,
    get_confirm_keyboard,
    get_back_keyboard
)
from config import (
    ADMIN_IDS,
    SESSION_TIMEOUT_MINUTES,
    ENABLE_USER_ACTIVITY_TRACKING
)
from monitoring.metrics import metrics_collector

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = Router()

class UserStates(StatesGroup):
    """User state machine states."""
    waiting_for_name = State()
    waiting_for_password = State()
    waiting_for_confirmation = State()

@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext) -> None:
    """Handle /start command."""
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS
    
    # Get or create user
    user = await db.get_user(user_id)
    if not user:
        # Register new user
        user_data = {
            "telegram_id": user_id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
            "role": UserRole.ADMIN.value if is_admin else UserRole.USER.value
        }
        await db.register_user(user_data)
        logger.info(f"New user registered: {user_id}")
    
    # Update user activity
    if ENABLE_USER_ACTIVITY_TRACKING:
        await db.register_user({
            "telegram_id": user_id,
            "last_active": datetime.now().isoformat()
        })
    
    # Track metrics
    metrics_collector.increment_message_count()
    
    # Send welcome message
    welcome_text = (
        "👋 Добро пожаловать в Корпоративную Базу Знаний!\n\n"
        "Я помогу вам изучить нашу продукцию и пройти тестирование.\n\n"
    )
    
    if is_admin:
        welcome_text += (
            "🔐 Вы авторизованы как администратор.\n"
            "Используйте /admin для доступа к панели управления."
        )
        keyboard = get_admin_menu_keyboard()
    else:
        welcome_text += (
            "📚 Доступные команды:\n"
            "/catalog - Просмотр каталога продукции\n"
            "/search - Поиск по базе знаний\n"
            "/tests - Доступные тесты\n"
            "/help - Справка по использованию бота"
        )
        keyboard = get_main_menu_keyboard()
    
    await message.answer(welcome_text, reply_markup=keyboard)
    await state.clear()

@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    """Handle /help command."""
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS
    
    help_text = (
        "📚 <b>Справка по использованию бота</b>\n\n"
        "Основные команды:\n"
        "/start - Начать работу с ботом\n"
        "/catalog - Просмотр каталога продукции\n"
        "/search - Поиск по базе знаний\n"
        "/tests - Доступные тесты\n"
        "/help - Показать эту справку\n\n"
        "Для поиска информации используйте команду /search\n"
        "Для прохождения тестов используйте команду /tests\n"
        "Для просмотра каталога используйте команду /catalog"
    )
    
    if is_admin:
        help_text += "\n\n<b>Команды администратора:</b>\n"
        help_text += "/admin - Панель управления\n"
        help_text += "/stats - Статистика использования\n"
    
    await message.answer(help_text)
    metrics_collector.increment_message_count()

@router.message(Command("profile"))
async def profile_handler(message: Message) -> None:
    """Handle /profile command."""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer(
            "❌ Профиль не найден. Используйте /start для регистрации."
        )
        return
    
    # Calculate session time remaining
    session_time = None
    if user.get("last_active"):
        last_active = datetime.fromisoformat(user["last_active"])
        session_end = last_active + timedelta(minutes=SESSION_TIMEOUT_MINUTES)
        if datetime.now() < session_end:
            session_time = (session_end - datetime.now()).total_seconds() / 60
    
    # Format profile information
    profile_text = (
        "👤 <b>Ваш профиль</b>\n\n"
        f"ID: {user['telegram_id']}\n"
        f"Имя: {user['first_name'] or 'Не указано'}\n"
        f"Фамилия: {user['last_name'] or 'Не указано'}\n"
        f"Username: @{user['username'] or 'Не указан'}\n"
        f"Роль: {user['role']}\n"
        f"Дата регистрации: {user['created_at']}\n"
    )
    
    if session_time:
        profile_text += f"\n⏳ Время до окончания сессии: {session_time:.0f} мин."
    
    # Add admin-specific information
    if user_id in ADMIN_IDS:
        profile_text += "\n\n🔐 Статус: Администратор"
    
    await message.answer(profile_text)
    metrics_collector.increment_message_count()

@router.message(Command("logout"))
async def logout_handler(message: Message, state: FSMContext) -> None:
    """Handle /logout command."""
    user_id = message.from_user.id
    
    # Clear user session
    await db.execute(
        "DELETE FROM user_sessions WHERE user_id = ?",
        (user_id,)
    )
    
    await message.answer(
        "👋 Вы успешно вышли из системы.\n"
        "Используйте /start для повторного входа.",
        reply_markup=get_main_menu_keyboard()
    )
    await state.clear()
    metrics_collector.increment_message_count()

@router.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle 'Back to main menu' callback."""
    user_id = callback.from_user.id
    is_admin = user_id in ADMIN_IDS
    
    await callback.message.edit_text(
        "Главное меню",
        reply_markup=get_admin_menu_keyboard() if is_admin else get_main_menu_keyboard()
    )
    await state.clear()
    await callback.answer()
    metrics_collector.increment_message_count()

@router.callback_query(F.data == "confirm_action")
async def confirm_action_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle action confirmation."""
    state_data = await state.get_data()
    action = state_data.get("action")
    
    if not action:
        await callback.answer("Ошибка: действие не определено")
        return
    
    try:
        if action == "delete_account":
            # Delete user account
            await db.execute(
                "DELETE FROM users WHERE telegram_id = ?",
                (callback.from_user.id,)
            )
            await callback.message.edit_text(
                "❌ Ваш аккаунт удален.\n"
                "Используйте /start для регистрации нового аккаунта."
            )
        else:
            await callback.answer("Неизвестное действие")
            return
        
        await state.clear()
        metrics_collector.increment_message_count()
    
    except Exception as e:
        logger.error(f"Error in confirm_action_handler: {e}")
        await callback.answer("Произошла ошибка при выполнении действия")
        metrics_collector.increment_error_count()

@router.callback_query(F.data == "cancel_action")
async def cancel_action_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle action cancellation."""
    await callback.message.edit_text(
        "Действие отменено",
        reply_markup=get_main_menu_keyboard()
    )
    await state.clear()
    await callback.answer()
    metrics_collector.increment_message_count()

def setup_user_handlers(dp: Router) -> None:
    """Register user handlers with the dispatcher."""
    dp.include_router(router)
    logger.info("User handlers registered") 