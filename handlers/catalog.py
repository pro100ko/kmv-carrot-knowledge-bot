"""Catalog handlers for product browsing and management."""

import logging
from typing import Optional, Dict, List
from datetime import datetime

from aiogram import Router, F, Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from utils.keyboards import (
    get_catalog_keyboard,
    get_product_keyboard,
    get_pagination_keyboard,
    get_confirm_keyboard,
    get_back_keyboard
)
from utils.db_pool import db_pool
from monitoring.metrics import metrics_collector
from config import ADMIN_IDS

router = Router()
logger = logging.getLogger(__name__)

class CatalogStates(StatesGroup):
    """States for catalog interactions."""
    browsing_category = State()
    viewing_product = State()
    waiting_for_search = State()

@router.message(Command("catalog"))
@router.message(F.text == "📚 Каталог")
async def show_catalog(message: Message, state: FSMContext):
    """Show main catalog categories."""
    try:
        # Get categories from database
        categories = await db_pool.fetchall(
            "SELECT id, name, description FROM categories WHERE is_active = 1"
        )
        
        if not categories:
            await message.answer(
                "😔 В каталоге пока нет категорий.",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Format categories message
        categories_text = "📚 Доступные категории:\n\n"
        for category in categories:
            categories_text += f"• {category['name']}\n"
            if category['description']:
                categories_text += f"  {category['description']}\n"
        
        await message.answer(
            categories_text,
            reply_markup=get_catalog_keyboard(categories)
        )
        await state.set_state(CatalogStates.browsing_category)
        
        # Track metrics
        metrics_collector.increment_message_count()
        
    except Exception as e:
        logger.error(f"Error showing catalog: {e}")
        await message.answer(
            "😔 Произошла ошибка при загрузке каталога. Попробуйте позже.",
            reply_markup=get_back_keyboard()
        )

@router.callback_query(F.data.startswith("category_"))
async def show_category_products(callback: CallbackQuery, state: FSMContext):
    """Show products in selected category."""
    try:
        category_id = int(callback.data.split("_")[1])
        
        # Get category info
        category = await db_pool.fetchone(
            "SELECT name, description FROM categories WHERE id = ?",
            (category_id,)
        )
        
        if not category:
            await callback.answer("Категория не найдена")
            return
        
        # Get products in category
        products = await db_pool.fetchall(
            """
            SELECT id, name, description, price 
            FROM products 
            WHERE category_id = ? AND is_active = 1
            ORDER BY name
            """,
            (category_id,)
        )
        
        if not products:
            await callback.message.edit_text(
                f"😔 В категории '{category['name']}' пока нет товаров.",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Format products message
        products_text = f"📚 {category['name']}\n"
        if category['description']:
            products_text += f"{category['description']}\n\n"
        
        products_text += "Доступные товары:\n\n"
        for product in products:
            products_text += f"• {product['name']}\n"
            if product['description']:
                products_text += f"  {product['description']}\n"
            if product['price']:
                products_text += f"  💰 {product['price']} руб.\n"
        
        # Add pagination if needed
        page = 1
        items_per_page = 5
        total_pages = (len(products) + items_per_page - 1) // items_per_page
        
        await callback.message.edit_text(
            products_text,
            reply_markup=get_pagination_keyboard(
                page,
                total_pages,
                f"category_{category_id}"
            )
        )
        
        # Store category info in state
        await state.update_data(
            current_category=category_id,
            current_page=page
        )
        
        # Track metrics
        metrics_collector.increment_message_count()
        
    except Exception as e:
        logger.error(f"Error showing category products: {e}")
        await callback.message.edit_text(
            "😔 Произошла ошибка при загрузке товаров. Попробуйте позже.",
            reply_markup=get_back_keyboard()
        )

@router.callback_query(F.data.startswith("category_") & F.data.endswith("_page_"))
async def show_category_page(callback: CallbackQuery, state: FSMContext):
    """Show specific page of category products."""
    try:
        # Parse callback data
        parts = callback.data.split("_")
        category_id = int(parts[1])
        page = int(parts[-1])
        
        # Get category info
        category = await db_pool.fetchone(
            "SELECT name, description FROM categories WHERE id = ?",
            (category_id,)
        )
        
        if not category:
            await callback.answer("Категория не найдена")
            return
        
        # Get products with pagination
        items_per_page = 5
        offset = (page - 1) * items_per_page
        
        products = await db_pool.fetchall(
            """
            SELECT id, name, description, price 
            FROM products 
            WHERE category_id = ? AND is_active = 1
            ORDER BY name
            LIMIT ? OFFSET ?
            """,
            (category_id, items_per_page, offset)
        )
        
        if not products:
            await callback.answer("Нет товаров на этой странице")
            return
        
        # Format products message
        products_text = f"📚 {category['name']}\n"
        if category['description']:
            products_text += f"{category['description']}\n\n"
        
        products_text += "Доступные товары:\n\n"
        for product in products:
            products_text += f"• {product['name']}\n"
            if product['description']:
                products_text += f"  {product['description']}\n"
            if product['price']:
                products_text += f"  💰 {product['price']} руб.\n"
        
        # Get total pages
        total_count = await db_pool.fetchone(
            "SELECT COUNT(*) as count FROM products WHERE category_id = ? AND is_active = 1",
            (category_id,)
        )
        total_pages = (total_count['count'] + items_per_page - 1) // items_per_page
        
        await callback.message.edit_text(
            products_text,
            reply_markup=get_pagination_keyboard(
                page,
                total_pages,
                f"category_{category_id}"
            )
        )
        
        # Update state
        await state.update_data(
            current_category=category_id,
            current_page=page
        )
        
        # Track metrics
        metrics_collector.increment_message_count()
        
    except Exception as e:
        logger.error(f"Error showing category page: {e}")
        await callback.message.edit_text(
            "😔 Произошла ошибка при загрузке страницы. Попробуйте позже.",
            reply_markup=get_back_keyboard()
        )

@router.callback_query(F.data.startswith("product_"))
async def show_product(callback: CallbackQuery, state: FSMContext):
    """Show detailed product information."""
    try:
        product_id = int(callback.data.split("_")[1])
        is_admin = callback.from_user.id in ADMIN_IDS
        
        # Get product info
        product = await db_pool.fetchone(
            """
            SELECT p.*, c.name as category_name 
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE p.id = ? AND p.is_active = 1
            """,
            (product_id,)
        )
        
        if not product:
            await callback.answer("Товар не найден")
            return
        
        # Format product message
        product_text = f"📦 {product['name']}\n"
        product_text += f"📚 Категория: {product['category_name']}\n"
        
        if product['description']:
            product_text += f"\n📝 Описание:\n{product['description']}\n"
        
        if product['price']:
            product_text += f"\n💰 Цена: {product['price']} руб.\n"
        
        if product['specifications']:
            product_text += f"\n📋 Характеристики:\n{product['specifications']}\n"
        
        # Check if product has tests
        has_tests = await db_pool.fetchone(
            "SELECT COUNT(*) as count FROM tests WHERE product_id = ? AND is_active = 1",
            (product_id,)
        )
        
        await callback.message.edit_text(
            product_text,
            reply_markup=get_product_keyboard(
                product_id,
                is_admin=is_admin
            )
        )
        
        # Update state
        await state.set_state(CatalogStates.viewing_product)
        await state.update_data(current_product=product_id)
        
        # Track metrics
        metrics_collector.increment_message_count()
        
    except Exception as e:
        logger.error(f"Error showing product: {e}")
        await callback.message.edit_text(
            "😔 Произошла ошибка при загрузке товара. Попробуйте позже.",
            reply_markup=get_back_keyboard()
        )

@router.message(Command("search"))
@router.message(F.text == "🔍 Поиск")
async def start_search(message: Message, state: FSMContext):
    """Start product search process."""
    await message.answer(
        "🔍 Введите поисковый запрос (название или описание товара):",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(CatalogStates.waiting_for_search)

@router.message(CatalogStates.waiting_for_search)
async def process_search(message: Message, state: FSMContext):
    """Process search query and show results."""
    try:
        query = message.text.strip()
        if not query:
            await message.answer(
                "❌ Поисковый запрос не может быть пустым. Попробуйте еще раз:",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Search products
        products = await db_pool.fetchall(
            """
            SELECT p.*, c.name as category_name 
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE p.is_active = 1 
            AND (
                p.name LIKE ? 
                OR p.description LIKE ? 
                OR p.specifications LIKE ?
            )
            ORDER BY p.name
            LIMIT 10
            """,
            (f"%{query}%", f"%{query}%", f"%{query}%")
        )
        
        if not products:
            await message.answer(
                f"😔 По запросу '{query}' ничего не найдено.",
                reply_markup=get_back_keyboard()
            )
            await state.clear()
            return
        
        # Format search results
        results_text = f"🔍 Результаты поиска по запросу '{query}':\n\n"
        for product in products:
            results_text += f"• {product['name']}\n"
            results_text += f"  📚 Категория: {product['category_name']}\n"
            if product['price']:
                results_text += f"  💰 {product['price']} руб.\n"
            results_text += "\n"
        
        await message.answer(
            results_text,
            reply_markup=get_back_keyboard()
        )
        
        # Track metrics
        metrics_collector.increment_message_count()
        
        # Clear search state
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error processing search: {e}")
        await message.answer(
            "😔 Произошла ошибка при поиске. Попробуйте позже.",
            reply_markup=get_back_keyboard()
        )
        await state.clear()

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Return to main menu."""
    await state.clear()
    await callback.message.edit_text(
        "Выберите действие:",
        reply_markup=get_back_keyboard()
    )

@router.callback_query(F.data == "back_to_catalog")
async def back_to_catalog(callback: CallbackQuery, state: FSMContext):
    """Return to catalog view."""
    await state.set_state(CatalogStates.browsing_category)
    await show_catalog(callback.message, state)

def setup_catalog_handlers(dp: Dispatcher) -> None:
    """Register catalog handlers with the dispatcher."""
    dp.include_router(router) 