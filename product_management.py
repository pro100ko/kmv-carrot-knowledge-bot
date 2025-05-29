from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from datetime import datetime
import re
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, MediaGroup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import (
    MAX_PRODUCT_IMAGES,
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
    AdminProductCallback,
    truncate_message
)

# Create router for product management
router = Router()

# States for product forms
class ProductForm(StatesGroup):
    category = State()
    name = State()
    description = State()
    price = State()
    images = State()

@dataclass
class ProductValidation:
    """Product data validation results"""
    is_valid: bool
    errors: List[str]
    data: Optional[Dict[str, Any]] = None

def validate_product_name(name: str) -> ProductValidation:
    """Validate product name"""
    errors = []
    
    if not name:
        errors.append("Название товара не может быть пустым")
    elif len(name) < 2:
        errors.append("Название товара должно содержать минимум 2 символа")
    elif len(name) > 100:
        errors.append("Название товара не должно превышать 100 символов")
    elif not re.match(r'^[\w\s\-.,!?()]+$', name):
        errors.append("Название товара содержит недопустимые символы")
    
    return ProductValidation(
        is_valid=len(errors) == 0,
        errors=errors,
        data={"name": name.strip()} if not errors else None
    )

def validate_product_description(description: str) -> ProductValidation:
    """Validate product description"""
    errors = []
    
    if description and len(description) > 1000:
        errors.append("Описание товара не должно превышать 1000 символов")
    elif description and not re.match(r'^[\w\s\-.,!?()\n]+$', description):
        errors.append("Описание товара содержит недопустимые символы")
    
    return ProductValidation(
        is_valid=len(errors) == 0,
        errors=errors,
        data={"description": description.strip()} if not errors else None
    )

def validate_product_price(price: str) -> ProductValidation:
    """Validate product price"""
    errors = []
    
    if not price:
        errors.append("Цена товара не может быть пустой")
    else:
        try:
            # Try to parse price as decimal
            price_decimal = Decimal(price.replace(',', '.'))
            if price_decimal < 0:
                errors.append("Цена не может быть отрицательной")
            elif price_decimal > 999999.99:
                errors.append("Цена не может превышать 999999.99")
            else:
                # Format price with 2 decimal places
                formatted_price = f"{price_decimal:.2f}"
                return ProductValidation(
                    is_valid=True,
                    errors=[],
                    data={"price": formatted_price}
                )
        except InvalidOperation:
            errors.append("Некорректный формат цены")
    
    return ProductValidation(
        is_valid=len(errors) == 0,
        errors=errors
    )

def get_product_keyboard(
    product_id: int,
    category_id: Optional[int] = None,
    page: int = 1
) -> InlineKeyboardMarkup:
    """Generate keyboard for product view"""
    builder = InlineKeyboardBuilder()
    
    # Get product data
    product = db.get_product(product_id)
    if not product:
        raise ValueError("Товар не найден")
    
    # Add admin buttons if user is admin
    if is_admin(product.get('created_by')):
        builder.button(
            text="✏️ Редактировать",
            callback_data=AdminProductCallback(
                action="edit",
                product_id=product_id
            ).pack()
        )
        builder.button(
            text="🖼 Управление изображениями",
            callback_data=AdminProductCallback(
                action="manage_images",
                product_id=product_id
            ).pack()
        )
        builder.button(
            text="✅ Активировать" if not product['is_active'] else "❌ Деактивировать",
            callback_data=AdminProductCallback(
                action="toggle_active",
                product_id=product_id
            ).pack()
        )
        builder.button(
            text="🗑 Удалить",
            callback_data=AdminProductCallback(
                action="delete",
                product_id=product_id
            ).pack()
        )
    
    # Add back button
    if category_id:
        builder.button(
            text="◀️ Назад к категории",
            callback_data=f"category:{category_id}"
        )
    else:
        builder.button(
            text="◀️ Назад к товарам",
            callback_data=AdminProductCallback(
                action="list",
                category_id=product['category_id'],
                page=page
            ).pack()
        )
    
    # Adjust layout
    builder.adjust(1)  # One button per row
    return builder.as_markup()

def format_product_message(product: Dict[str, Any]) -> str:
    """Format product message with proper HTML formatting"""
    # Get category info
    category = db.get_category(product['category_id'])
    
    # Format basic info
    message = (
        f"<b>{product['name']}</b>\n\n"
        f"{product['description'] or 'Нет описания'}\n\n"
        f"<b>Категория:</b> {category['name']}\n"
        f"<b>Цена:</b> {product['price_info'] or 'Не указана'}\n"
        f"<b>Статус:</b> {'✅ Активен' if product['is_active'] else '❌ Неактивен'}\n\n"
    )
    
    # Add image count
    images = product.get('images', [])
    message += f"<b>Изображений:</b> {len(images)}\n\n"
    
    # Add creation info
    message += (
        f"<i>Создано: {product['created_at']}\n"
        f"Последнее обновление: {product['updated_at']}</i>"
    )
    
    return truncate_message(message)

def search_products(query: str) -> List[Dict[str, Any]]:
    """Search products by name or description"""
    if not query:
        return []
    
    # Get all products
    products = []
    categories = db.get_categories(include_inactive=True)
    for category in categories:
        products.extend(db.get_products_by_category(category['id'], include_inactive=True))
    
    # Search in name and description
    query = query.lower()
    results = []
    
    for product in products:
        if (query in product['name'].lower() or
            (product['description'] and query in product['description'].lower())):
            results.append(product)
    
    return results

def get_product_stats(product_id: int) -> Dict[str, Any]:
    """Get product statistics"""
    product = db.get_product(product_id)
    if not product:
        raise ValueError("Товар не найден")
    
    # Get basic stats
    views = product.get('views', 0)
    interactions = product.get('interactions', 0)
    
    return {
        "product_id": product_id,
        "name": product['name'],
        "category_id": product['category_id'],
        "views": views,
        "interactions": interactions,
        "interaction_rate": (interactions / views * 100) if views else 0,
        "is_active": product['is_active'],
        "created_at": product['created_at'],
        "updated_at": product['updated_at']
    }

# Command handlers
@router.message(Command("products"))
async def list_products_command(message: Message) -> None:
    """Handle /products command"""
    try:
        # Get all products
        products = []
        categories = db.get_categories()
        for category in categories:
            products.extend(db.get_products_by_category(category['id']))
        
        if not products:
            await message.answer(
                "Товары пока не добавлены.",
                parse_mode="HTML"
            )
            return
        
        text = format_admin_message(
            title="📦 Товары",
            content="\n\n".join(
                f"• {prod['name']} ({prod['price_info'] or 'Цена не указана'})\n"
                f"  Категория: {db.get_category(prod['category_id'])['name']}"
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
        keyboard.adjust(1)
        
        await message.answer(text, reply_markup=keyboard.as_markup())
        
    except Exception as e:
        admin_logger.error(f"Error in list products command: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        )

# Callback handlers
@router.callback_query(F.data.startswith("product:"))
async def product_callback(callback: CallbackQuery) -> None:
    """Handle product selection callback"""
    try:
        product_id = int(callback.data.split(":")[1])
        product = db.get_product(product_id)
        
        if not product:
            raise ValueError("Товар не найден")
        
        # Update product views
        db.update_product(product_id, {"views": product.get("views", 0) + 1})
        
        # Format and send message
        text = format_product_message(product)
        keyboard = get_product_keyboard(product_id)
        
        # Send images if available
        images = product.get('images', [])
        if images:
            media = MediaGroup()
            for i, image in enumerate(images):
                if i == 0:
                    # First image with caption
                    media.attach_photo(
                        image['file_id'],
                        caption=text,
                        parse_mode="HTML"
                    )
                else:
                    # Other images without caption
                    media.attach_photo(image['file_id'])
            
            await callback.message.answer_media_group(media)
            await callback.message.delete()
        else:
            await edit_message(callback, text, keyboard)
        
    except Exception as e:
        admin_logger.error(f"Error in product callback: {e}")
        await callback.answer(
            format_error_message(e),
            show_alert=True
        )

# Form handlers
@router.message(ProductForm.category)
async def process_product_category(message: Message, state: FSMContext) -> None:
    """Process product category selection"""
    try:
        # Get category ID from callback data
        if not message.text.startswith("category:"):
            await message.answer(
                format_admin_message(
                    title="❌ Ошибка",
                    content="Пожалуйста, выберите категорию из списка."
                )
            )
            return
        
        category_id = int(message.text.split(":")[1])
        category = db.get_category(category_id)
        
        if not category:
            raise ValueError("Категория не найдена")
        
        # Save category and request name
        await state.update_data(category_id=category_id)
        await state.set_state(ProductForm.name)
        
        await message.answer(
            format_admin_message(
                title="📦 Создание товара",
                content=f"Введите название товара для категории {category['name']}:"
            )
        )
        
    except Exception as e:
        admin_logger.error(f"Error in process product category: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        )
        await state.clear()

@router.message(ProductForm.name)
async def process_product_name(message: Message, state: FSMContext) -> None:
    """Process product name input"""
    try:
        # Validate name
        validation = validate_product_name(message.text)
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
        await state.set_state(ProductForm.description)
        
        await message.answer(
            format_admin_message(
                title="📦 Создание товара",
                content="Введите описание товара (или отправьте '-' для пропуска):"
            )
        )
        
    except Exception as e:
        admin_logger.error(f"Error in process product name: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        )
        await state.clear()

@router.message(ProductForm.description)
async def process_product_description(message: Message, state: FSMContext) -> None:
    """Process product description input"""
    try:
        # Get saved data
        data = await state.get_data()
        
        # Validate description
        description = None if message.text == "-" else message.text
        validation = validate_product_description(description) if description else ProductValidation(True, [])
        
        if not validation.is_valid:
            await message.answer(
                format_admin_message(
                    title="❌ Ошибка валидации",
                    content="\n".join(validation.errors)
                )
            )
            return
        
        # Save description and request price
        await state.update_data(description=validation.data["description"] if description else None)
        await state.set_state(ProductForm.price)
        
        await message.answer(
            format_admin_message(
                title="📦 Создание товара",
                content="Введите цену товара (например: 1000.50):"
            )
        )
        
    except Exception as e:
        admin_logger.error(f"Error in process product description: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        )
        await state.clear()

@router.message(ProductForm.price)
async def process_product_price(message: Message, state: FSMContext) -> None:
    """Process product price input"""
    try:
        # Validate price
        validation = validate_product_price(message.text)
        if not validation.is_valid:
            await message.answer(
                format_admin_message(
                    title="❌ Ошибка валидации",
                    content="\n".join(validation.errors)
                )
            )
            return
        
        # Save price and request images
        await state.update_data(price=validation.data["price"])
        await state.set_state(ProductForm.images)
        
        await message.answer(
            format_admin_message(
                title="📦 Создание товара",
                content=(
                    f"Отправьте изображения товара "
                    f"(или отправьте '-' для пропуска, максимум {MAX_PRODUCT_IMAGES}):"
                )
            )
        )
        
    except Exception as e:
        admin_logger.error(f"Error in process product price: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        )
        await state.clear()

@router.message(ProductForm.images)
async def process_product_images(message: Message, state: FSMContext) -> None:
    """Process product images input"""
    try:
        # Get saved data
        data = await state.get_data()
        
        # Handle images or skip
        if message.text == "-":
            images_data = []
        elif message.photo:
            # Get the largest photo
            photo = message.photo[-1]
            images_data = [{
                "file_id": photo.file_id,
                "file_unique_id": photo.file_unique_id,
                "width": photo.width,
                "height": photo.height,
                "file_size": photo.file_size
            }]
        else:
            await message.answer(
                format_admin_message(
                    title="❌ Ошибка",
                    content="Пожалуйста, отправьте изображение или '-' для пропуска."
                )
            )
            return
        
        # Create product
        product_data = {
            "category_id": data["category_id"],
            "name": data["name"],
            "description": data["description"],
            "price_info": data["price"],
            "images": images_data,
            "created_by": message.from_user.id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_active": True
        }
        
        product_id = db.add_product(product_data)
        
        # Send success message
        product = db.get_product(product_id)
        text = format_admin_message(
            title="✅ Товар создан",
            content=format_product_message(product)
        )
        keyboard = get_product_keyboard(product_id)
        
        # Send images if available
        if images_data:
            media = MediaGroup()
            for i, image in enumerate(images_data):
                if i == 0:
                    # First image with caption
                    media.attach_photo(
                        image['file_id'],
                        caption=text,
                        parse_mode="HTML"
                    )
                else:
                    # Other images without caption
                    media.attach_photo(image['file_id'])
            
            await message.answer_media_group(media)
        else:
            await message.answer(text, reply_markup=keyboard)
        
        await state.clear()
        
    except Exception as e:
        admin_logger.error(f"Error in process product images: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        )
        await state.clear()

# Search handler
@router.message(Command("search_product"))
async def search_product_command(message: Message) -> None:
    """Handle /search_product command"""
    try:
        # Get search query
        query = message.text.replace("/search_product", "").strip()
        
        if not query:
            await message.answer(
                format_admin_message(
                    title="🔍 Поиск товаров",
                    content="Используйте команду в формате:\n/search_product <запрос>"
                )
            )
            return
        
        # Search products
        results = search_products(query)
        
        if not results:
            await message.answer(
                format_admin_message(
                    title="🔍 Поиск товаров",
                    content=f"По запросу '{query}' ничего не найдено."
                )
            )
            return
        
        # Format results
        text = format_admin_message(
            title=f"🔍 Результаты поиска: {query}",
            content="\n\n".join(
                f"• {prod['name']}\n"
                f"  {prod['description'] or 'Нет описания'}\n"
                f"  Цена: {prod['price_info'] or 'Не указана'}\n"
                f"  Категория: {db.get_category(prod['category_id'])['name']}"
                for prod in results
            )
        )
        
        # Create keyboard with product buttons
        keyboard = InlineKeyboardBuilder()
        for product in results:
            keyboard.button(
                text=product['name'],
                callback_data=f"product:{product['id']}"
            )
        keyboard.adjust(1)
        
        await message.answer(text, reply_markup=keyboard.as_markup())
        
    except Exception as e:
        admin_logger.error(f"Error in search product command: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        ) 