from typing import Dict, List, Optional, Union, Any
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    CallbackQuery
)
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
import logging

from config import (
    ADMIN_IDS,
    MAX_MESSAGE_LENGTH,
    MAX_CAPTION_LENGTH,
    ENABLE_ADMIN_PANEL
)
from logging_config import admin_logger
from sqlite_db import db
from utils.message_utils import format_error_message, truncate_message

# Setup logging
logger = logging.getLogger(__name__)

# Initialize router
router = Router()

# Callback data classes for admin panel
class AdminCallback(CallbackData, prefix="admin"):
    action: str
    target: Optional[str] = None
    id: Optional[int] = None
    page: Optional[int] = None

class AdminCategoryCallback(CallbackData, prefix="admin_cat"):
    action: str
    category_id: Optional[int] = None
    page: Optional[int] = None

class AdminProductCallback(CallbackData, prefix="admin_prod"):
    action: str
    product_id: Optional[int] = None
    category_id: Optional[int] = None
    page: Optional[int] = None

class AdminTestCallback(CallbackData, prefix="admin_test"):
    action: str
    test_id: Optional[int] = None
    page: Optional[int] = None

class AdminStatsCallback(CallbackData, prefix="admin_stats"):
    action: str
    target: Optional[str] = None
    period: Optional[str] = None
    page: Optional[int] = None

class AdminStates(StatesGroup):
    """States for admin panel operations"""
    waiting_for_action = State()
    waiting_for_category_name = State()
    waiting_for_category_description = State()
    waiting_for_category_image = State()
    waiting_for_confirmation = State()

def is_admin(user_id: int) -> bool:
    """Check if user is an admin"""
    if not ENABLE_ADMIN_PANEL:
        return False
    return user_id in ADMIN_IDS

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Generate main admin panel keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📁 Категории", callback_data=AdminCallback(action="categories").pack())
    builder.button(text="📦 Товары", callback_data=AdminCallback(action="products").pack())
    builder.button(text="📝 Тесты", callback_data=AdminCallback(action="tests").pack())
    builder.button(text="📊 Статистика", callback_data=AdminCallback(action="stats").pack())
    
    builder.adjust(2)  # 2 buttons per row
    return builder.as_markup()

def get_categories_keyboard(page: int = 1, per_page: int = 5) -> InlineKeyboardMarkup:
    """Generate categories management keyboard"""
    builder = InlineKeyboardBuilder()
    
    # Get categories for current page
    categories = db.get_categories(include_inactive=True)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_categories = categories[start_idx:end_idx]
    
    # Add category buttons
    for category in page_categories:
        builder.button(
            text=f"{'✅' if category['is_active'] else '❌'} {category['name']}",
            callback_data=AdminCategoryCallback(
                action="edit",
                category_id=category['id']
            ).pack()
        )
    
    # Add navigation buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=AdminCategoryCallback(
                    action="list",
                    page=page-1
                ).pack()
            )
        )
    if end_idx < len(categories):
        nav_buttons.append(
            InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=AdminCategoryCallback(
                    action="list",
                    page=page+1
                ).pack()
            )
        )
    
    # Add action buttons
    action_buttons = [
        InlineKeyboardButton(
            text="➕ Добавить категорию",
            callback_data=AdminCategoryCallback(action="create").pack()
        ),
        InlineKeyboardButton(
            text="🔍 Поиск",
            callback_data=AdminCategoryCallback(action="search").pack()
        ),
        InlineKeyboardButton(
            text="◀️ Назад в админ-панель",
            callback_data=AdminCallback(action="main").pack()
        )
    ]
    
    # Add all buttons to keyboard
    builder.add(*nav_buttons)
    builder.add(*action_buttons)
    
    # Adjust layout
    builder.adjust(1)  # One button per row for categories
    return builder.as_markup()

def get_products_keyboard(category_id: Optional[int] = None, page: int = 1, per_page: int = 5) -> InlineKeyboardMarkup:
    """Generate products management keyboard"""
    builder = InlineKeyboardBuilder()
    
    # Get products for current page
    if category_id:
        products = db.get_products_by_category(category_id, include_inactive=True)
    else:
        # Get all products if no category specified
        products = []
        categories = db.get_categories(include_inactive=True)
        for category in categories:
            products.extend(db.get_products_by_category(category['id'], include_inactive=True))
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_products = products[start_idx:end_idx]
    
    # Add product buttons
    for product in page_products:
        builder.button(
            text=f"{'✅' if product['is_active'] else '❌'} {product['name']}",
            callback_data=AdminProductCallback(
                action="edit",
                product_id=product['id']
            ).pack()
        )
    
    # Add navigation buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=AdminProductCallback(
                    action="list",
                    category_id=category_id,
                    page=page-1
                ).pack()
            )
        )
    if end_idx < len(products):
        nav_buttons.append(
            InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=AdminProductCallback(
                    action="list",
                    category_id=category_id,
                    page=page+1
                ).pack()
            )
        )
    
    # Add action buttons
    action_buttons = [
        InlineKeyboardButton(
            text="➕ Добавить товар",
            callback_data=AdminProductCallback(
                action="create",
                category_id=category_id
            ).pack()
        ),
        InlineKeyboardButton(
            text="🔍 Поиск",
            callback_data=AdminProductCallback(action="search").pack()
        )
    ]
    
    if category_id:
        action_buttons.append(
            InlineKeyboardButton(
                text="◀️ Назад к категориям",
                callback_data=AdminCallback(action="categories").pack()
            )
        )
    else:
        action_buttons.append(
            InlineKeyboardButton(
                text="◀️ Назад в админ-панель",
                callback_data=AdminCallback(action="main").pack()
            )
        )
    
    # Add all buttons to keyboard
    builder.add(*nav_buttons)
    builder.add(*action_buttons)
    
    # Adjust layout
    builder.adjust(1)  # One button per row for products
    return builder.as_markup()

def get_tests_keyboard(page: int = 1, per_page: int = 5) -> InlineKeyboardMarkup:
    """Generate tests management keyboard"""
    builder = InlineKeyboardBuilder()
    
    # Get tests for current page
    tests = db.get_tests_list()
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_tests = tests[start_idx:end_idx]
    
    # Add test buttons
    for test in page_tests:
        builder.button(
            text=f"{test['title']} ({test['attempts_count']} попыток)",
            callback_data=AdminTestCallback(
                action="edit",
                test_id=test['id']
            ).pack()
        )
    
    # Add navigation buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=AdminTestCallback(
                    action="list",
                    page=page-1
                ).pack()
            )
        )
    if end_idx < len(tests):
        nav_buttons.append(
            InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=AdminTestCallback(
                    action="list",
                    page=page+1
                ).pack()
            )
        )
    
    # Add action buttons
    action_buttons = [
        InlineKeyboardButton(
            text="➕ Добавить тест",
            callback_data=AdminTestCallback(action="create").pack()
        ),
        InlineKeyboardButton(
            text="🔍 Поиск",
            callback_data=AdminTestCallback(action="search").pack()
        ),
        InlineKeyboardButton(
            text="◀️ Назад в админ-панель",
            callback_data=AdminCallback(action="main").pack()
        )
    ]
    
    # Add all buttons to keyboard
    builder.add(*nav_buttons)
    builder.add(*action_buttons)
    
    # Adjust layout
    builder.adjust(1)  # One button per row for tests
    return builder.as_markup()

def get_stats_keyboard() -> InlineKeyboardMarkup:
    """Generate statistics keyboard"""
    builder = InlineKeyboardBuilder()
    
    # Add statistics buttons
    builder.button(
        text="👥 Пользователи",
        callback_data=AdminStatsCallback(action="users").pack()
    )
    builder.button(
        text="📊 Тесты",
        callback_data=AdminStatsCallback(action="tests").pack()
    )
    builder.button(
        text="📈 Продукты",
        callback_data=AdminStatsCallback(action="products").pack()
    )
    builder.button(
        text="◀️ Назад в админ-панель",
        callback_data=AdminCallback(action="main").pack()
    )
    
    # Adjust layout
    builder.adjust(2)  # 2 buttons per row
    return builder.as_markup()

async def edit_message(
    message: Union[Message, CallbackQuery],
    text: str,
    keyboard: Optional[InlineKeyboardMarkup] = None,
    parse_mode: str = "HTML"
) -> None:
    """Edit message with proper error handling"""
    try:
        if isinstance(message, CallbackQuery):
            await message.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
        else:
            await message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            # Message content hasn't changed, ignore error
            pass
        else:
            admin_logger.error(f"Failed to edit message: {e}")
            raise

def format_admin_message(
    title: str,
    content: str,
    footer: Optional[str] = None
) -> str:
    """Format admin panel message with proper HTML formatting"""
    message = f"<b>{title}</b>\n\n{content}"
    if footer:
        message += f"\n\n{footer}"
    return message

def truncate_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> str:
    """Truncate message if it exceeds maximum length"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def format_error_message(error: Exception) -> str:
    """Format error message for admin panel"""
    return format_admin_message(
        title="❌ Ошибка",
        content=f"Произошла ошибка: {str(error)}",
        footer="Пожалуйста, попробуйте еще раз или обратитесь к разработчику."
    )

def create_admin_keyboard() -> InlineKeyboardMarkup:
    """Create main admin panel keyboard"""
    builder = InlineKeyboardBuilder()
    
    # Main actions
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="👥 Пользователи", callback_data="admin_users")
    builder.button(text="📚 Категории", callback_data="admin_categories")
    builder.button(text="📦 Продукты", callback_data="admin_products")
    builder.button(text="📝 Тесты", callback_data="admin_tests")
    builder.button(text="⚙️ Настройки", callback_data="admin_settings")
    
    builder.adjust(2)  # Two buttons per row
    return builder.as_markup()

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Show admin panel"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⚠️ У вас нет прав для выполнения этой команды.")
        return
    
    await message.answer(
        "⚙️ <b>Панель управления</b>\n\n"
        "Выберите действие:",
        reply_markup=create_admin_keyboard()
    )

@router.callback_query(F.data == "admin_stats")
async def process_admin_stats(callback: CallbackQuery):
    """Show admin statistics"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет прав для выполнения этой команды")
        return
    
    try:
        # Get statistics
        user_stats = db.get_user_stats()
        test_stats = db.get_test_stats()
        db_stats = db.get_database_stats()
        
        stats_text = (
            "📊 <b>Статистика системы</b>\n\n"
            f"👥 <b>Пользователи:</b>\n"
            f"Всего: {user_stats['total_users']}\n"
            f"Активных: {user_stats['active_users']}\n"
            f"Администраторов: {user_stats['admin_users']}\n\n"
            f"📝 <b>Тесты:</b>\n"
            f"Всего: {test_stats['total_tests']}\n"
            f"Активных: {test_stats['active_tests']}\n"
            f"Всего попыток: {test_stats['total_attempts']}\n"
            f"Средний балл: {test_stats['avg_score']:.1f}%\n\n"
            f"💾 <b>База данных:</b>\n"
            f"Размер: {db_stats['size_mb']:.1f} MB\n"
            f"Таблиц: {db_stats['tables']}\n"
            f"Записей: {db_stats['records']}\n"
            f"Последнее обновление: {db_stats['last_update']}"
        )
        
        # Create keyboard
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Обновить", callback_data="admin_stats")
        builder.button(text="◀️ Назад", callback_data="admin_back")
        builder.adjust(2)
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        await callback.message.edit_text(
            "⚠️ Произошла ошибка при получении статистики.\n"
            "Пожалуйста, попробуйте позже."
        )

@router.callback_query(F.data == "admin_users")
async def process_admin_users(callback: CallbackQuery):
    """Show user management"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет прав для выполнения этой команды")
        return
    
    try:
        # Get user statistics
        stats = db.get_user_stats()
        users = stats['users']
        
        # Sort users by last activity
        users.sort(key=lambda x: x.get('last_active', ''), reverse=True)
        
        # Create user list
        user_list = []
        for user in users[:10]:  # Show top 10 most active users
            last_active = datetime.fromisoformat(user['last_active']).strftime('%d.%m.%Y %H:%M')
            user_list.append(
                f"👤 {user['first_name']} {user['last_name']}\n"
                f"ID: {user['telegram_id']}\n"
                f"Тестов: {user['tests_completed']}\n"
                f"Ср. балл: {user['avg_score']:.1f}%\n"
                f"Последняя активность: {last_active}\n"
            )
        
        users_text = (
            "👥 <b>Управление пользователями</b>\n\n"
            f"Всего пользователей: {stats['total_users']}\n"
            f"Активных: {stats['active_users']}\n"
            f"Администраторов: {stats['admin_users']}\n\n"
            "<b>Последние активные пользователи:</b>\n"
            + "\n".join(user_list)
        )
        
        # Create keyboard
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Обновить", callback_data="admin_users")
        builder.button(text="◀️ Назад", callback_data="admin_back")
        builder.adjust(2)
        
        await callback.message.edit_text(
            users_text,
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        logger.error(f"Error getting user list: {e}")
        await callback.message.edit_text(
            "⚠️ Произошла ошибка при получении списка пользователей.\n"
            "Пожалуйста, попробуйте позже."
        )

@router.callback_query(F.data == "admin_categories")
async def process_admin_categories(callback: CallbackQuery):
    """Show category management"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет прав для выполнения этой команды")
        return
    
    try:
        # Get categories
        categories = db.get_categories(include_inactive=True)
        
        # Create category list
        category_list = []
        for category in categories:
            products = db.get_products_by_category(category['id'], include_inactive=False)
            status = "✅" if category['is_active'] else "❌"
            category_list.append(
                f"{status} {category['name']}\n"
                f"ID: {category['id']}\n"
                f"Продуктов: {len(products)}\n"
            )
        
        categories_text = (
            "📚 <b>Управление категориями</b>\n\n"
            f"Всего категорий: {len(categories)}\n\n"
            "<b>Список категорий:</b>\n"
            + "\n".join(category_list)
        )
        
        # Create keyboard
        builder = InlineKeyboardBuilder()
        builder.button(text="➕ Добавить", callback_data="category_add")
        builder.button(text="🔄 Обновить", callback_data="admin_categories")
        builder.button(text="◀️ Назад", callback_data="admin_back")
        builder.adjust(2)
        
        await callback.message.edit_text(
            categories_text,
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        logger.error(f"Error getting category list: {e}")
        await callback.message.edit_text(
            "⚠️ Произошла ошибка при получении списка категорий.\n"
            "Пожалуйста, попробуйте позже."
        )

@router.callback_query(F.data == "admin_products")
async def process_admin_products(callback: CallbackQuery):
    """Show product management"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет прав для выполнения этой команды")
        return
    
    try:
        # Get all products
        categories = db.get_categories(include_inactive=False)
        total_products = 0
        product_list = []
        
        for category in categories:
            products = db.get_products_by_category(category['id'], include_inactive=True)
            total_products += len(products)
            
            if products:
                product_list.append(f"\n📁 <b>{category['name']}</b>")
                for product in products:
                    status = "✅" if product['is_active'] else "❌"
                    product_list.append(
                        f"{status} {product['name']}\n"
                        f"ID: {product['id']}\n"
                    )
        
        products_text = (
            "📦 <b>Управление продуктами</b>\n\n"
            f"Всего продуктов: {total_products}\n"
            "<b>Список продуктов по категориям:</b>\n"
            + "\n".join(product_list)
        )
        
        # Create keyboard
        builder = InlineKeyboardBuilder()
        builder.button(text="➕ Добавить", callback_data="product_add")
        builder.button(text="🔄 Обновить", callback_data="admin_products")
        builder.button(text="◀️ Назад", callback_data="admin_back")
        builder.adjust(2)
        
        await callback.message.edit_text(
            products_text,
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        logger.error(f"Error getting product list: {e}")
        await callback.message.edit_text(
            "⚠️ Произошла ошибка при получении списка продуктов.\n"
            "Пожалуйста, попробуйте позже."
        )

@router.callback_query(F.data == "admin_tests")
async def process_admin_tests(callback: CallbackQuery):
    """Show test management"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет прав для выполнения этой команды")
        return
    
    try:
        # Get all tests
        tests = db.get_tests_list(include_inactive=True)
        
        # Get test statistics
        stats = db.get_test_stats()
        test_stats = {s['test_id']: s for s in stats['tests']}
        
        # Create test list
        test_list = []
        for test in tests:
            stats = test_stats.get(test['id'], {'attempts': 0, 'avg_score': 0})
            status = "✅" if test['is_active'] else "❌"
            test_list.append(
                f"{status} {test['title']}\n"
                f"ID: {test['id']}\n"
                f"Попыток: {stats['attempts']}\n"
                f"Ср. балл: {stats['avg_score']:.1f}%\n"
            )
        
        tests_text = (
            "📝 <b>Управление тестами</b>\n\n"
            f"Всего тестов: {len(tests)}\n\n"
            "<b>Список тестов:</b>\n"
            + "\n".join(test_list)
        )
        
        # Create keyboard
        builder = InlineKeyboardBuilder()
        builder.button(text="➕ Добавить", callback_data="test_add")
        builder.button(text="🔄 Обновить", callback_data="admin_tests")
        builder.button(text="◀️ Назад", callback_data="admin_back")
        builder.adjust(2)
        
        await callback.message.edit_text(
            tests_text,
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        logger.error(f"Error getting test list: {e}")
        await callback.message.edit_text(
            "⚠️ Произошла ошибка при получении списка тестов.\n"
            "Пожалуйста, попробуйте позже."
        )

@router.callback_query(F.data == "admin_settings")
async def process_admin_settings(callback: CallbackQuery):
    """Show admin settings"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет прав для выполнения этой команды")
        return
    
    try:
        # Get database statistics
        db_stats = db.get_database_stats()
        
        settings_text = (
            "⚙️ <b>Настройки системы</b>\n\n"
            f"💾 <b>База данных:</b>\n"
            f"Размер: {db_stats['size_mb']:.1f} MB\n"
            f"Таблиц: {db_stats['tables']}\n"
            f"Записей: {db_stats['records']}\n"
            f"Последнее обновление: {db_stats['last_update']}\n\n"
            "Доступные действия:\n"
            "• Оптимизация базы данных\n"
            "• Создание резервной копии\n"
            "• Очистка старых данных"
        )
        
        # Create keyboard
        builder = InlineKeyboardBuilder()
        builder.button(text="💾 Создать бэкап", callback_data="admin_backup")
        builder.button(text="🔄 Оптимизировать БД", callback_data="admin_vacuum")
        builder.button(text="🗑 Очистить данные", callback_data="admin_cleanup")
        builder.button(text="◀️ Назад", callback_data="admin_back")
        builder.adjust(2)
        
        await callback.message.edit_text(
            settings_text,
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        await callback.message.edit_text(
            "⚠️ Произошла ошибка при получении настроек.\n"
            "Пожалуйста, попробуйте позже."
        )

@router.callback_query(F.data == "admin_backup")
async def process_admin_backup(callback: CallbackQuery):
    """Create database backup"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет прав для выполнения этой команды")
        return
    
    try:
        # Create backup
        db._backup_database()
        
        # Get backup files
        backups = db.get_backup_files()
        
        backup_text = (
            "💾 <b>Резервные копии базы данных</b>\n\n"
            f"Последняя копия создана: {backups[0]['created_at']}\n"
            f"Размер: {backups[0]['size_mb']:.1f} MB\n\n"
            "Доступные копии:\n"
        )
        
        for backup in backups[:5]:  # Show last 5 backups
            backup_text += f"• {backup['created_at']} ({backup['size_mb']:.1f} MB)\n"
        
        # Create keyboard
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Создать новую копию", callback_data="admin_backup")
        builder.button(text="🗑 Очистить старые копии", callback_data="admin_cleanup_backups")
        builder.button(text="◀️ Назад", callback_data="admin_settings")
        builder.adjust(2)
        
        await callback.message.edit_text(
            backup_text,
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        await callback.message.edit_text(
            "⚠️ Произошла ошибка при создании резервной копии.\n"
            "Пожалуйста, попробуйте позже."
        )

@router.callback_query(F.data == "admin_vacuum")
async def process_admin_vacuum(callback: CallbackQuery):
    """Optimize database"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет прав для выполнения этой команды")
        return
    
    try:
        # Get initial size
        initial_size = db.get_database_size()
        
        # Optimize database
        db.vacuum()
        
        # Get new size
        new_size = db.get_database_size()
        saved = (initial_size - new_size) / 1024 / 1024  # Convert to MB
        
        await callback.message.edit_text(
            f"✅ База данных оптимизирована!\n\n"
            f"Освобождено места: {saved:.1f} MB\n"
            f"Новый размер: {new_size / 1024 / 1024:.1f} MB",
            reply_markup=InlineKeyboardBuilder()
            .button(text="◀️ Назад", callback_data="admin_settings")
            .as_markup()
        )
        
    except Exception as e:
        logger.error(f"Error optimizing database: {e}")
        await callback.message.edit_text(
            "⚠️ Произошла ошибка при оптимизации базы данных.\n"
            "Пожалуйста, попробуйте позже."
        )

@router.callback_query(F.data == "admin_cleanup")
async def process_admin_cleanup(callback: CallbackQuery):
    """Clean up old data"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет прав для выполнения этой команды")
        return
    
    try:
        # Clean up old backups
        db.cleanup_old_backups()
        
        # Get current stats
        db_stats = db.get_database_stats()
        
        await callback.message.edit_text(
            "✅ Очистка данных выполнена!\n\n"
            f"Текущий размер БД: {db_stats['size_mb']:.1f} MB\n"
            f"Количество записей: {db_stats['records']}",
            reply_markup=InlineKeyboardBuilder()
            .button(text="◀️ Назад", callback_data="admin_settings")
            .as_markup()
        )
        
    except Exception as e:
        logger.error(f"Error cleaning up data: {e}")
        await callback.message.edit_text(
            "⚠️ Произошла ошибка при очистке данных.\n"
            "Пожалуйста, попробуйте позже."
        )

@router.callback_query(F.data == "admin_back")
async def process_admin_back(callback: CallbackQuery):
    """Return to main admin menu"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет прав для выполнения этой команды")
        return
    
    await callback.message.edit_text(
        "⚙️ <b>Панель управления</b>\n\n"
        "Выберите действие:",
        reply_markup=create_admin_keyboard()
    )

def setup_admin_handlers(dp: Router):
    """Setup admin panel handlers"""
    dp.include_router(router) 