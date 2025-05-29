from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from datetime import datetime
import re

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import (
    MAX_CATEGORY_IMAGES,
    MAX_MESSAGE_LENGTH,
    MAX_CAPTION_LENGTH
)
from logging_config import admin_logger
from sqlite_db import db
from admin_panel import (
    is_admin,
    edit_message,
    format_admin_message,
    format_error_message,
    AdminCategoryCallback,
    truncate_message
)

# Create router for category management
router = Router()

# States for category forms
class CategoryForm(StatesGroup):
    name = State()
    description = State()
    image = State()

@dataclass
class CategoryValidation:
    """Category data validation results"""
    is_valid: bool
    errors: List[str]
    data: Optional[Dict[str, Any]] = None

def validate_category_name(name: str) -> CategoryValidation:
    """Validate category name"""
    errors = []
    
    if not name:
        errors.append("Название категории не может быть пустым")
    elif len(name) < 2:
        errors.append("Название категории должно содержать минимум 2 символа")
    elif len(name) > 100:
        errors.append("Название категории не должно превышать 100 символов")
    elif not re.match(r'^[\w\s\-.,!?()]+$', name):
        errors.append("Название категории содержит недопустимые символы")
    
    return CategoryValidation(
        is_valid=len(errors) == 0,
        errors=errors,
        data={"name": name.strip()} if not errors else None
    )

def validate_category_description(description: str) -> CategoryValidation:
    """Validate category description"""
    errors = []
    
    if description and len(description) > 1000:
        errors.append("Описание категории не должно превышать 1000 символов")
    elif description and not re.match(r'^[\w\s\-.,!?()\n]+$', description):
        errors.append("Описание категории содержит недопустимые символы")
    
    return CategoryValidation(
        is_valid=len(errors) == 0,
        errors=errors,
        data={"description": description.strip()} if not errors else None
    )

def get_category_keyboard(
    category_id: int,
    page: int = 1,
    include_products: bool = True
) -> InlineKeyboardMarkup:
    """Generate keyboard for category view"""
    builder = InlineKeyboardBuilder()
    
    # Get category data
    category = db.get_category(category_id)
    if not category:
        raise ValueError("Категория не найдена")
    
    # Add product buttons if requested
    if include_products:
        products = db.get_products_by_category(category_id)
        for product in products[:5]:  # Show first 5 products
            builder.button(
                text=f"{'✅' if product['is_active'] else '❌'} {product['name']}",
                callback_data=f"product:{product['id']}"
            )
    
    # Add navigation buttons
    if include_products and len(products) > 5:
        builder.button(
            text="📦 Все товары",
            callback_data=f"category_products:{category_id}"
        )
    
    # Add admin buttons if user is admin
    if is_admin(category.get('created_by')):
        builder.button(
            text="✏️ Редактировать",
            callback_data=AdminCategoryCallback(
                action="edit",
                category_id=category_id
            ).pack()
        )
        builder.button(
            text="🗑 Удалить",
            callback_data=AdminCategoryCallback(
                action="delete",
                category_id=category_id
            ).pack()
        )
    
    # Add back button
    builder.button(
        text="◀️ Назад",
        callback_data="knowledge_base"
    )
    
    # Adjust layout
    builder.adjust(1)  # One button per row
    return builder.as_markup()

def format_category_message(category: Dict[str, Any]) -> str:
    """Format category message with proper HTML formatting"""
    # Format basic info
    message = (
        f"<b>{category['name']}</b>\n\n"
        f"{category['description'] or 'Нет описания'}\n\n"
    )
    
    # Add product count
    products = db.get_products_by_category(category['id'])
    active_products = sum(1 for p in products if p['is_active'])
    message += (
        f"<b>Товаров:</b> {len(products)}\n"
        f"<b>Активных:</b> {active_products}\n"
        f"<b>Неактивных:</b> {len(products) - active_products}\n\n"
    )
    
    # Add creation info
    message += (
        f"<i>Создано: {category['created_at']}\n"
        f"Последнее обновление: {category['updated_at']}</i>"
    )
    
    return truncate_message(message)

def search_categories(query: str) -> List[Dict[str, Any]]:
    """Search categories by name or description"""
    if not query:
        return []
    
    # Get all categories
    categories = db.get_categories(include_inactive=True)
    
    # Search in name and description
    query = query.lower()
    results = []
    
    for category in categories:
        if (query in category['name'].lower() or
            (category['description'] and query in category['description'].lower())):
            results.append(category)
    
    return results

def get_category_stats(category_id: int) -> Dict[str, Any]:
    """Get category statistics"""
    category = db.get_category(category_id)
    if not category:
        raise ValueError("Категория не найдена")
    
    products = db.get_products_by_category(category_id)
    active_products = sum(1 for p in products if p['is_active'])
    
    # Calculate views and interactions
    total_views = sum(p.get('views', 0) for p in products)
    total_interactions = sum(p.get('interactions', 0) for p in products)
    
    return {
        "category_id": category_id,
        "name": category['name'],
        "total_products": len(products),
        "active_products": active_products,
        "inactive_products": len(products) - active_products,
        "total_views": total_views,
        "total_interactions": total_interactions,
        "interaction_rate": (total_interactions / total_views * 100) if total_views else 0,
        "created_at": category['created_at'],
        "updated_at": category['updated_at']
    }

# Command handlers
@router.message(Command("categories"))
async def list_categories_command(message: Message) -> None:
    """Handle /categories command"""
    try:
        categories = db.get_categories()
        
        if not categories:
            await message.answer(
                "Категории пока не добавлены.",
                parse_mode="HTML"
            )
            return
        
        text = format_admin_message(
            title="📁 Категории",
            content="\n\n".join(
                f"• {cat['name']} ({len(db.get_products_by_category(cat['id']))} товаров)"
                for cat in categories
            )
        )
        
        # Create keyboard with category buttons
        keyboard = InlineKeyboardBuilder()
        for category in categories:
            keyboard.button(
                text=category['name'],
                callback_data=f"category:{category['id']}"
            )
        keyboard.adjust(1)
        
        await message.answer(text, reply_markup=keyboard.as_markup())
        
    except Exception as e:
        admin_logger.error(f"Error in list categories command: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        )

# Callback handlers
@router.callback_query(F.data.startswith("category:"))
async def category_callback(callback: CallbackQuery) -> None:
    """Handle category selection callback"""
    try:
        category_id = int(callback.data.split(":")[1])
        category = db.get_category(category_id)
        
        if not category:
            raise ValueError("Категория не найдена")
        
        # Update category views
        db.update_category(category_id, {"views": category.get("views", 0) + 1})
        
        # Format and send message
        text = format_category_message(category)
        keyboard = get_category_keyboard(category_id)
        
        await edit_message(callback, text, keyboard)
        
    except Exception as e:
        admin_logger.error(f"Error in category callback: {e}")
        await callback.answer(
            format_error_message(e),
            show_alert=True
        )

@router.callback_query(F.data.startswith("category_products:"))
async def category_products_callback(callback: CallbackQuery) -> None:
    """Handle category products list callback"""
    try:
        category_id = int(callback.data.split(":")[1])
        category = db.get_category(category_id)
        
        if not category:
            raise ValueError("Категория не найдена")
        
        products = db.get_products_by_category(category_id)
        
        if not products:
            await callback.answer(
                "В этой категории пока нет товаров.",
                show_alert=True
            )
            return
        
        text = format_admin_message(
            title=f"📦 Товары в категории {category['name']}",
            content="\n\n".join(
                f"• {prod['name']}\n"
                f"  {'✅ Активен' if prod['is_active'] else '❌ Неактивен'}\n"
                f"  {prod['description'] or 'Нет описания'}"
                for prod in products
            )
        )
        
        # Create keyboard with product buttons
        keyboard = InlineKeyboardBuilder()
        for product in products:
            keyboard.button(
                text=product['name'],
                callback_data=f"product:{product['id']}"
            )
        keyboard.button(
            text="◀️ Назад к категории",
            callback_data=f"category:{category_id}"
        )
        keyboard.adjust(1)
        
        await edit_message(callback, text, keyboard.as_markup())
        
    except Exception as e:
        admin_logger.error(f"Error in category products callback: {e}")
        await callback.answer(
            format_error_message(e),
            show_alert=True
        )

# Form handlers
@router.message(CategoryForm.name)
async def process_category_name(message: Message, state: FSMContext) -> None:
    """Process category name input"""
    try:
        # Validate name
        validation = validate_category_name(message.text)
        if not validation.is_valid:
            await message.answer(
                format_admin_message(
                    title="❌ Ошибка валидации",
                    content="\n".join(validation.errors)
                )
            )
            return
        
        # Save name and request description
        await state.update_data(name=validation.data["name"])
        await state.set_state(CategoryForm.description)
        
        await message.answer(
            format_admin_message(
                title="📁 Создание категории",
                content="Введите описание категории (или отправьте '-' для пропуска):"
            )
        )
        
    except Exception as e:
        admin_logger.error(f"Error in process category name: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        )
        await state.clear()

@router.message(CategoryForm.description)
async def process_category_description(message: Message, state: FSMContext) -> None:
    """Process category description input"""
    try:
        # Get saved data
        data = await state.get_data()
        
        # Validate description
        description = None if message.text == "-" else message.text
        validation = validate_category_description(description) if description else CategoryValidation(True, [])
        
        if not validation.is_valid:
            await message.answer(
                format_admin_message(
                    title="❌ Ошибка валидации",
                    content="\n".join(validation.errors)
                )
            )
            return
        
        # Save description and request image
        await state.update_data(description=validation.data["description"] if description else None)
        await state.set_state(CategoryForm.image)
        
        await message.answer(
            format_admin_message(
                title="📁 Создание категории",
                content=(
                    "Отправьте изображение для категории "
                    f"(или отправьте '-' для пропуска, максимум {MAX_CATEGORY_IMAGES}):"
                )
            )
        )
        
    except Exception as e:
        admin_logger.error(f"Error in process category description: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        )
        await state.clear()

@router.message(CategoryForm.image)
async def process_category_image(message: Message, state: FSMContext) -> None:
    """Process category image input"""
    try:
        # Get saved data
        data = await state.get_data()
        
        # Handle image or skip
        if message.text == "-":
            image_data = None
        elif message.photo:
            # Get the largest photo
            photo = message.photo[-1]
            image_data = {
                "file_id": photo.file_id,
                "file_unique_id": photo.file_unique_id,
                "width": photo.width,
                "height": photo.height,
                "file_size": photo.file_size
            }
        else:
            await message.answer(
                format_admin_message(
                    title="❌ Ошибка",
                    content="Пожалуйста, отправьте изображение или '-' для пропуска."
                )
            )
            return
        
        # Create category
        category_data = {
            "name": data["name"],
            "description": data["description"],
            "image": image_data,
            "created_by": message.from_user.id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_active": True
        }
        
        category_id = db.add_category(category_data)
        
        # Send success message
        category = db.get_category(category_id)
        text = format_admin_message(
            title="✅ Категория создана",
            content=format_category_message(category)
        )
        keyboard = get_category_keyboard(category_id)
        
        await message.answer(text, reply_markup=keyboard)
        await state.clear()
        
    except Exception as e:
        admin_logger.error(f"Error in process category image: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        )
        await state.clear()

# Search handler
@router.message(Command("search_category"))
async def search_category_command(message: Message) -> None:
    """Handle /search_category command"""
    try:
        # Get search query
        query = message.text.replace("/search_category", "").strip()
        
        if not query:
            await message.answer(
                format_admin_message(
                    title="🔍 Поиск категорий",
                    content="Используйте команду в формате:\n/search_category <запрос>"
                )
            )
            return
        
        # Search categories
        results = search_categories(query)
        
        if not results:
            await message.answer(
                format_admin_message(
                    title="🔍 Поиск категорий",
                    content=f"По запросу '{query}' ничего не найдено."
                )
            )
            return
        
        # Format results
        text = format_admin_message(
            title=f"🔍 Результаты поиска: {query}",
            content="\n\n".join(
                f"• {cat['name']}\n"
                f"  {cat['description'] or 'Нет описания'}\n"
                f"  Товаров: {len(db.get_products_by_category(cat['id']))}"
                for cat in results
            )
        )
        
        # Create keyboard with category buttons
        keyboard = InlineKeyboardBuilder()
        for category in results:
            keyboard.button(
                text=category['name'],
                callback_data=f"category:{category['id']}"
            )
        keyboard.adjust(1)
        
        await message.answer(text, reply_markup=keyboard.as_markup())
        
    except Exception as e:
        admin_logger.error(f"Error in search category command: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        ) 