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

from config import (
    ADMIN_IDS,
    MAX_MESSAGE_LENGTH,
    MAX_CAPTION_LENGTH,
    ENABLE_ADMIN_PANEL
)
from logging_config import admin_logger
from sqlite_db import db

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