from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from enum import Enum

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, User
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import (
    ADMIN_IDS,
    MAX_MESSAGE_LENGTH,
    SESSION_TIMEOUT_MINUTES
)
from logging_config import admin_logger, user_logger
from sqlite_db import db
from admin_panel import (
    is_admin,
    edit_message,
    format_admin_message,
    format_error_message,
    AdminUserCallback,
    truncate_message
)

# Create router for user management
router = Router()

# User roles
class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

# States for user forms
class UserForm(StatesGroup):
    name = State()
    email = State()
    phone = State()
    role = State()

@dataclass
class UserValidation:
    """User data validation results"""
    is_valid: bool
    errors: List[str]
    data: Optional[Dict[str, Any]] = None

def validate_user_name(name: str) -> UserValidation:
    """Validate user name"""
    errors = []
    
    if not name:
        errors.append("Имя пользователя не может быть пустым")
    elif len(name) < 2:
        errors.append("Имя пользователя должно содержать минимум 2 символа")
    elif len(name) > 100:
        errors.append("Имя пользователя не должно превышать 100 символов")
    elif not re.match(r'^[\w\s\-.,!?()]+$', name):
        errors.append("Имя пользователя содержит недопустимые символы")
    
    return UserValidation(
        is_valid=len(errors) == 0,
        errors=errors,
        data={"name": name.strip()} if not errors else None
    )

def validate_user_email(email: str) -> UserValidation:
    """Validate user email"""
    errors = []
    
    if not email:
        errors.append("Email не может быть пустым")
    elif not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        errors.append("Некорректный формат email")
    elif len(email) > 100:
        errors.append("Email не должен превышать 100 символов")
    
    return UserValidation(
        is_valid=len(errors) == 0,
        errors=errors,
        data={"email": email.lower().strip()} if not errors else None
    )

def validate_user_phone(phone: str) -> UserValidation:
    """Validate user phone number"""
    errors = []
    
    if not phone:
        errors.append("Номер телефона не может быть пустым")
    elif not re.match(r'^\+?[\d\s\-()]{10,15}$', phone):
        errors.append("Некорректный формат номера телефона")
    
    return UserValidation(
        is_valid=len(errors) == 0,
        errors=errors,
        data={"phone": phone.strip()} if not errors else None
    )

def get_user_keyboard(
    user_id: int,
    page: int = 1,
    include_stats: bool = True
) -> InlineKeyboardMarkup:
    """Generate keyboard for user view"""
    builder = InlineKeyboardBuilder()
    
    # Get user data
    user = db.get_user(user_id)
    if not user:
        raise ValueError("Пользователь не найден")
    
    # Add admin buttons if current user is admin
    if is_admin(user.get('created_by')):
        builder.button(
            text="✏️ Редактировать",
            callback_data=AdminUserCallback(
                action="edit",
                user_id=user_id
            ).pack()
        )
        builder.button(
            text="👥 Изменить роль",
            callback_data=AdminUserCallback(
                action="change_role",
                user_id=user_id
            ).pack()
        )
        builder.button(
            text="✅ Активировать" if not user['is_active'] else "❌ Деактивировать",
            callback_data=AdminUserCallback(
                action="toggle_active",
                user_id=user_id
            ).pack()
        )
        builder.button(
            text="🗑 Удалить",
            callback_data=AdminUserCallback(
                action="delete",
                user_id=user_id
            ).pack()
        )
    
    # Add back button
    builder.button(
        text="◀️ Назад",
        callback_data="admin_users"
    )
    
    # Adjust layout
    builder.adjust(1)  # One button per row
    return builder.as_markup()

def format_user_message(user: Dict[str, Any]) -> str:
    """Format user message with proper HTML formatting"""
    # Format basic info
    message = (
        f"<b>👤 {user['name']}</b>\n\n"
        f"<b>Telegram ID:</b> {user['telegram_id']}\n"
        f"<b>Email:</b> {user.get('email', 'Не указан')}\n"
        f"<b>Телефон:</b> {user.get('phone', 'Не указан')}\n"
        f"<b>Роль:</b> {user.get('role', UserRole.USER).value}\n"
        f"<b>Статус:</b> {'✅ Активен' if user['is_active'] else '❌ Неактивен'}\n\n"
    )
    
    # Add statistics if available
    stats = get_user_stats(user['id'])
    if stats:
        message += (
            f"<b>Статистика:</b>\n"
            f"• Последний вход: {stats['last_login']}\n"
            f"• Всего тестов: {stats['total_tests']}\n"
            f"• Успешных тестов: {stats['successful_tests']}\n"
            f"• Средний балл: {stats['average_score']:.1f}%\n"
            f"• Активность: {stats['activity_level']}\n\n"
        )
    
    # Add creation info
    message += (
        f"<i>Зарегистрирован: {user['created_at']}\n"
        f"Последнее обновление: {user['updated_at']}</i>"
    )
    
    return truncate_message(message)

def search_users(query: str) -> List[Dict[str, Any]]:
    """Search users by name, email, or phone"""
    if not query:
        return []
    
    # Get all users
    users = db.get_users(include_inactive=True)
    
    # Search in name, email, and phone
    query = query.lower()
    results = []
    
    for user in users:
        if (query in user['name'].lower() or
            (user.get('email') and query in user['email'].lower()) or
            (user.get('phone') and query in user['phone'].lower())):
            results.append(user)
    
    return results

def get_user_stats(user_id: int) -> Dict[str, Any]:
    """Get user statistics"""
    user = db.get_user(user_id)
    if not user:
        raise ValueError("Пользователь не найден")
    
    # Get user activity
    activity = db.get_user_activity(user_id)
    if not activity:
        return None
    
    # Get test attempts
    attempts = db.get_user_test_attempts(user_id)
    total_tests = len(attempts)
    successful_tests = sum(1 for a in attempts if a['is_successful'])
    total_score = sum(a['score'] for a in attempts)
    
    # Calculate activity level
    last_week_activity = sum(1 for a in activity if 
        datetime.fromisoformat(a['timestamp']) > datetime.now() - timedelta(days=7))
    activity_level = "Высокая" if last_week_activity > 10 else "Средняя" if last_week_activity > 3 else "Низкая"
    
    return {
        "user_id": user_id,
        "name": user['name'],
        "last_login": activity[-1]['timestamp'] if activity else None,
        "total_tests": total_tests,
        "successful_tests": successful_tests,
        "success_rate": (successful_tests / total_tests * 100) if total_tests else 0,
        "average_score": total_score / total_tests if total_tests else 0,
        "activity_level": activity_level,
        "last_week_activity": last_week_activity
    }

def update_user_session(user_id: int) -> None:
    """Update user session timestamp"""
    try:
        db.update_user(user_id, {
            "last_activity": datetime.now().isoformat(),
            "session_expires": (datetime.now() + timedelta(minutes=SESSION_TIMEOUT_MINUTES)).isoformat()
        })
    except Exception as e:
        user_logger.error(f"Error updating user session: {e}")

def check_user_session(user_id: int) -> bool:
    """Check if user session is valid"""
    try:
        user = db.get_user(user_id)
        if not user:
            return False
        
        session_expires = datetime.fromisoformat(user['session_expires'])
        return datetime.now() < session_expires
    except Exception as e:
        user_logger.error(f"Error checking user session: {e}")
        return False

# Command handlers
@router.message(Command("profile"))
async def profile_command(message: Message) -> None:
    """Handle /profile command"""
    try:
        user = db.get_user(message.from_user.id)
        
        if not user:
            # Register new user
            user_data = {
                "telegram_id": message.from_user.id,
                "name": message.from_user.full_name,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "is_active": True,
                "role": UserRole.USER.value
            }
            user_id = db.add_user(user_data)
            user = db.get_user(user_id)
        
        # Update session
        update_user_session(user['id'])
        
        # Format and send message
        text = format_user_message(user)
        keyboard = get_user_keyboard(user['id'])
        
        await message.answer(text, reply_markup=keyboard)
        
    except Exception as e:
        user_logger.error(f"Error in profile command: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        )

@router.message(Command("users"))
async def list_users_command(message: Message) -> None:
    """Handle /users command (admin only)"""
    try:
        if not is_admin(message.from_user.id):
            await message.answer(
                format_error_message("У вас нет доступа к этой команде"),
                parse_mode="HTML"
            )
            return
        
        users = db.get_users()
        
        if not users:
            await message.answer(
                "Пользователи пока не зарегистрированы.",
                parse_mode="HTML"
            )
            return
        
        text = format_admin_message(
            title="👥 Пользователи",
            content="\n\n".join(
                f"• {user['name']}\n"
                f"  Telegram ID: {user['telegram_id']}\n"
                f"  Роль: {user.get('role', UserRole.USER).value}\n"
                f"  Статус: {'✅ Активен' if user['is_active'] else '❌ Неактивен'}"
                for user in users
            )
        )
        
        # Create keyboard with user buttons
        keyboard = InlineKeyboardBuilder()
        for user in users:
            keyboard.button(
                text=user['name'],
                callback_data=f"user:{user['id']}"
            )
        keyboard.adjust(1)
        
        await message.answer(text, reply_markup=keyboard.as_markup())
        
    except Exception as e:
        admin_logger.error(f"Error in list users command: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        )

# Callback handlers
@router.callback_query(F.data.startswith("user:"))
async def user_callback(callback: CallbackQuery) -> None:
    """Handle user selection callback"""
    try:
        if not is_admin(callback.from_user.id):
            await callback.answer(
                "У вас нет доступа к этой функции",
                show_alert=True
            )
            return
        
        user_id = int(callback.data.split(":")[1])
        user = db.get_user(user_id)
        
        if not user:
            raise ValueError("Пользователь не найден")
        
        # Format and send message
        text = format_user_message(user)
        keyboard = get_user_keyboard(user_id)
        
        await edit_message(callback, text, keyboard)
        
    except Exception as e:
        admin_logger.error(f"Error in user callback: {e}")
        await callback.answer(
            format_error_message(e),
            show_alert=True
        )

# Form handlers
@router.message(UserForm.name)
async def process_user_name(message: Message, state: FSMContext) -> None:
    """Process user name input"""
    try:
        # Validate name
        validation = validate_user_name(message.text)
        if not validation.is_valid:
            await message.answer(
                format_admin_message(
                    title="❌ Ошибка валидации",
                    content="\n".join(validation.errors)
                )
            )
            return
        
        # Save name and request email
        await state.update_data(name=validation.data["name"])
        await state.set_state(UserForm.email)
        
        await message.answer(
            format_admin_message(
                title="👤 Редактирование профиля",
                content="Введите email (или отправьте '-' для пропуска):"
            )
        )
        
    except Exception as e:
        user_logger.error(f"Error in process user name: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        )
        await state.clear()

@router.message(UserForm.email)
async def process_user_email(message: Message, state: FSMContext) -> None:
    """Process user email input"""
    try:
        # Get saved data
        data = await state.get_data()
        
        # Validate email
        email = None if message.text == "-" else message.text
        validation = validate_user_email(email) if email else UserValidation(True, [])
        
        if not validation.is_valid:
            await message.answer(
                format_admin_message(
                    title="❌ Ошибка валидации",
                    content="\n".join(validation.errors)
                )
            )
            return
        
        # Save email and request phone
        await state.update_data(email=validation.data["email"] if email else None)
        await state.set_state(UserForm.phone)
        
        await message.answer(
            format_admin_message(
                title="👤 Редактирование профиля",
                content="Введите номер телефона (или отправьте '-' для пропуска):"
            )
        )
        
    except Exception as e:
        user_logger.error(f"Error in process user email: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        )
        await state.clear()

@router.message(UserForm.phone)
async def process_user_phone(message: Message, state: FSMContext) -> None:
    """Process user phone input"""
    try:
        # Get saved data
        data = await state.get_data()
        
        # Validate phone
        phone = None if message.text == "-" else message.text
        validation = validate_user_phone(phone) if phone else UserValidation(True, [])
        
        if not validation.is_valid:
            await message.answer(
                format_admin_message(
                    title="❌ Ошибка валидации",
                    content="\n".join(validation.errors)
                )
            )
            return
        
        # Update user
        user_data = {
            "name": data["name"],
            "email": data.get("email"),
            "phone": validation.data["phone"] if phone else None,
            "updated_at": datetime.now().isoformat()
        }
        
        db.update_user(data["user_id"], user_data)
        
        # Send success message
        user = db.get_user(data["user_id"])
        text = format_admin_message(
            title="✅ Профиль обновлен",
            content=format_user_message(user)
        )
        keyboard = get_user_keyboard(user['id'])
        
        await message.answer(text, reply_markup=keyboard)
        await state.clear()
        
    except Exception as e:
        user_logger.error(f"Error in process user phone: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        )
        await state.clear()

# Search handler
@router.message(Command("search_user"))
async def search_user_command(message: Message) -> None:
    """Handle /search_user command (admin only)"""
    try:
        if not is_admin(message.from_user.id):
            await message.answer(
                format_error_message("У вас нет доступа к этой команде"),
                parse_mode="HTML"
            )
            return
        
        # Get search query
        query = message.text.replace("/search_user", "").strip()
        
        if not query:
            await message.answer(
                format_admin_message(
                    title="🔍 Поиск пользователей",
                    content="Используйте команду в формате:\n/search_user <запрос>"
                )
            )
            return
        
        # Search users
        results = search_users(query)
        
        if not results:
            await message.answer(
                format_admin_message(
                    title="🔍 Поиск пользователей",
                    content=f"По запросу '{query}' ничего не найдено."
                )
            )
            return
        
        # Format results
        text = format_admin_message(
            title=f"🔍 Результаты поиска: {query}",
            content="\n\n".join(
                f"• {user['name']}\n"
                f"  Telegram ID: {user['telegram_id']}\n"
                f"  Email: {user.get('email', 'Не указан')}\n"
                f"  Телефон: {user.get('phone', 'Не указан')}\n"
                f"  Роль: {user.get('role', UserRole.USER).value}"
                for user in results
            )
        )
        
        # Create keyboard with user buttons
        keyboard = InlineKeyboardBuilder()
        for user in results:
            keyboard.button(
                text=user['name'],
                callback_data=f"user:{user['id']}"
            )
        keyboard.adjust(1)
        
        await message.answer(text, reply_markup=keyboard.as_markup())
        
    except Exception as e:
        admin_logger.error(f"Error in search user command: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        ) 