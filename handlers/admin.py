from aiogram import F, types
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import uuid
import logging
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from utils.message_utils import safe_edit_message
from sqlite_db import db  # Import the database instance
import config # Import the config module directly
from config import ADMIN_IDS, ENABLE_ADMIN_PANEL # Keep these for direct access where needed
from utils.keyboards import (
    get_admin_keyboard, get_admin_categories_keyboard,
    get_admin_products_keyboard, get_admin_products_list_keyboard,
    get_admin_tests_keyboard, get_admin_stats_keyboard,
    get_cancel_keyboard, get_confirm_keyboard,
    get_admin_control_keyboard,
    get_back_keyboard,
    get_pagination_keyboard
)
from dispatcher import dp
from states import CategoryForm, ProductForm, TestForm
from monitoring.metrics import metrics_collector
from typing import Optional, Dict, List
from datetime import datetime, timedelta

# Import the global resources dictionary from main
# from main import app_resources

logger = logging.getLogger(__name__)

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
async def check_admin_access(user_id: int, query: types.CallbackQuery = None) -> bool:
    """Проверяет права администратора"""
    if user_id not in ADMIN_IDS:  # Updated to use ADMIN_IDS
        msg = "⛔ У вас нет доступа к административной панели"
        if query:
            await query.answer(msg)
        return False
    return True

async def admin_check_middleware(handler, event, data):
    if event.from_user.id not in ADMIN_IDS:
        await event.answer("Доступ запрещен")
        return
    return await handler(event, data)

async def safe_clear_state(state: FSMContext) -> None:
    """Safely clear the state, handling any errors"""
    if state is None:
        return
    
    try:
        current_state = await state.get_state()
        if current_state is not None:
            await state.clear()
            logger.debug(f"State cleared successfully. Previous state: {current_state}")
    except Exception as e:
        logger.warning(f"Failed to clear state: {e}")
        # Don't raise the exception, just log it

async def send_admin_menu(
    target: types.Message | types.CallbackQuery,
    text: str = "🔧 <b>Административная панель</b>\n\nВыберите раздел для управления:"
) -> None:
    """Отправляет/обновляет меню админки"""
    if isinstance(target, types.CallbackQuery):
        await target.answer()
        await safe_edit_message(
            message=target.message,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard()
        )
    else:
        await target.answer(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard()
        )

# ===== ОСНОВНЫЕ ОБРАБОТЧИКИ =====
@dp.callback_query()
async def debug_callback_handler(query: types.CallbackQuery):
    logger.info(f"DEBUG: Received callback query: {query.data} from user {query.from_user.id}")
    await query.answer("Неизвестная команда", show_alert=True)
    return False  # Continue to other handlers

@dp.message(Command("admin"))
@dp.callback_query(F.data == "admin")
async def admin_handler(update: types.Message | types.CallbackQuery, state: FSMContext) -> None:
    """Главное меню админки"""
    try:
        user_id = update.from_user.id
        if not await check_admin_access(user_id, update if isinstance(update, types.CallbackQuery) else None):
            return
        logger.info(f"Admin menu opened by user {user_id}")
        await safe_clear_state(state)
        # Create keyboard with unified callback data
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="📂 Категории", callback_data="category:list"),
                types.InlineKeyboardButton(text="🍎 Товары", callback_data="product:list")
            ],
            [
                types.InlineKeyboardButton(text="📝 Тесты", callback_data="test:list"),
                types.InlineKeyboardButton(text="📊 Статистика", callback_data="stats:list")
            ],
            [types.InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
        ])
        text = "🔧 <b>Административная панель</b>\n\nВыберите раздел для управления:"
        if isinstance(update, types.CallbackQuery):
            await update.answer()
            await safe_edit_message(
                message=update.message,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        else:
            await update.answer(
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"Error in admin_handler: {e}", exc_info=True)
        if isinstance(update, types.CallbackQuery):
            await update.answer("Произошла ошибка", show_alert=True)

# ===== КАТЕГОРИИ =====
@dp.callback_query(F.data == "admin_categories")
async def admin_categories_handler(query: types.CallbackQuery, state: FSMContext) -> None:
    """Управление категориями"""
    try:
        if not await check_admin_access(query.from_user.id, query):
            return
        
        logger.info(f"Categories menu opened by user {query.from_user.id}")
        await safe_clear_state(state)
        
        categories = db.get_categories()
        buttons = []
        
        # Add category buttons
        for cat in categories:
            buttons.append([
                types.InlineKeyboardButton(
                    text=f"✏️ {cat['name']}", 
                    callback_data=f"category_edit:{cat['id']}"
                )
            ])
        
        # Add create and back buttons
        buttons.extend([
            [types.InlineKeyboardButton(text="➕ Создать категорию", callback_data="create_category")],
            [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin")]
        ])
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
        
        text = "📂 <b>Управление категориями</b>\n\nВыберите категорию для редактирования или создайте новую:"
        if not categories:
            text = "📂 <b>Управление категориями</b>\n\nКатегории пока не созданы. Создайте первую категорию:"
        
        await query.answer()
        await safe_edit_message(
            message=query.message,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in admin_categories_handler: {e}", exc_info=True)
        await query.answer("Произошла ошибка при загрузке категорий", show_alert=True)

@dp.callback_query(F.data == "create_category")
async def create_category_handler(
    callback: types.CallbackQuery,
    state: FSMContext
) -> None:
    """Создание новой категории"""
    try:
        if not await check_admin_access(callback.from_user.id, callback):
            return
        
        logger.info(f"Category creation started by user {callback.from_user.id}")
        await safe_clear_state(state)
        await state.set_state(CategoryForm.name)
        await safe_edit_message(
            message=callback.message,
            text="✏️ Введите название новой категории:",
            reply_markup=get_cancel_keyboard("cancel_category_creation")
        )
    except Exception as e:
        logger.error(f"Error in create_category_handler: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при создании категории", show_alert=True)

@dp.callback_query(F.data.startswith("admin_category_edit:"))
async def admin_category_edit_handler(
    query: types.CallbackQuery,
    state: FSMContext
) -> None:
    """Редактирование категории"""
    try:
        if not await check_admin_access(query.from_user.id, query):
            return
        
        category_id = query.data.split(':')[1]
        logger.info(f"Admin editing category {category_id} by user {query.from_user.id}")
        
        category = next((c for c in db.get_categories() if c['id'] == category_id), None)
        if not category:
            logger.error(f"Category {category_id} not found")
            await query.answer("Категория не найдена", show_alert=True)
            return
        
        await state.set_state(CategoryForm.edit_name)
        await state.update_data(category_id=category_id)
        
        await safe_edit_message(
            message=query.message,
            text=f"✏️ Редактирование категории\n\nТекущее название: {category['name']}\n\nВведите новое название:",
            reply_markup=get_cancel_keyboard("cancel_category_edit")
        )
    except Exception as e:
        logger.error(f"Error in admin_category_edit_handler: {e}", exc_info=True)
        await query.answer("Произошла ошибка при редактировании категории", show_alert=True)

@dp.callback_query(F.data.startswith("admin_category_delete:"))
async def admin_category_delete_handler(
    query: types.CallbackQuery,
    state: FSMContext
) -> None:
    """Удаление категории"""
    try:
        if not await check_admin_access(query.from_user.id, query):
            return
        
        category_id = query.data.split(':')[1]
        logger.info(f"Admin deleting category {category_id} by user {query.from_user.id}")
        
        category = next((c for c in db.get_categories() if c['id'] == category_id), None)
        if not category:
            logger.error(f"Category {category_id} not found")
            await query.answer("Категория не найдена", show_alert=True)
            return
        
        # Check if category has products
        products = db.get_products_by_category(category_id)
        if products:
            await query.answer(
                "❌ Невозможно удалить категорию, содержащую товары.\n"
                "Сначала удалите или переместите все товары.",
                show_alert=True
            )
            return
        
        await state.set_state(CategoryForm.confirm_delete)
        await state.update_data(category_id=category_id)
        
        await safe_edit_message(
            message=query.message,
            text=f"⚠️ Подтверждение удаления\n\nВы уверены, что хотите удалить категорию '{category['name']}'?",
            reply_markup=get_confirm_keyboard(
                confirm_callback=f"confirm_category_delete:{category_id}",
                cancel_callback="cancel_category_delete"
            )
        )
    except Exception as e:
        logger.error(f"Error in admin_category_delete_handler: {e}", exc_info=True)
        await query.answer("Произошла ошибка при удалении категории", show_alert=True)

# ===== ТОВАРЫ =====
@dp.callback_query(F.data == "admin_products")
async def admin_products_handler(query: types.CallbackQuery, state: FSMContext) -> None:
    """Управление товарами"""
    try:
        if not await check_admin_access(query.from_user.id, query):
            return
        
        logger.info(f"Products menu opened by user {query.from_user.id}")
        await safe_clear_state(state)
        
        categories = db.get_categories()
        buttons = []
        
        # Add category buttons
        for cat in categories:
            buttons.append([
                types.InlineKeyboardButton(
                    text=f"📦 {cat['name']}", 
                    callback_data=f"product_category:{cat['id']}"
                )
            ])
        
        # Add search and back buttons
        buttons.extend([
            [types.InlineKeyboardButton(text="🔍 Поиск товаров", callback_data="admin_search_products")],
            [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin")]
        ])
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
        
        text = "🍎 <b>Управление товарами</b>\n\nВыберите категорию товаров:"
        if not categories:
            text = "🍎 <b>Управление товарами</b>\n\nСначала создайте категорию товаров."
        
        await query.answer()
        await safe_edit_message(
            message=query.message,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in admin_products_handler: {e}", exc_info=True)
        await query.answer("Произошла ошибка при загрузке меню товаров", show_alert=True)

@dp.callback_query(F.data.startswith("admin_products_category:"))
async def admin_products_category_handler(
    query: types.CallbackQuery,
    state: FSMContext
) -> None:
    """Показ товаров конкретной категории"""
    try:
        if not await check_admin_access(query.from_user.id, query):
            return
        
        category_id = query.data.split(':')[1]
        logger.info(f"Admin viewing products in category {category_id} by user {query.from_user.id}")
        
        products = db.get_products_by_category(category_id)
        category = next((c for c in db.get_categories() if c['id'] == category_id), None)
        
        if not category:
            logger.error(f"Category {category_id} not found")
            await query.answer("Категория не найдена", show_alert=True)
            return
        
        text = (
            f"🍎 <b>Управление товарами</b>\n\n"
            f"Категория: {category['name']}\n\n"
            f"Выберите товар для редактирования или создайте новый:"
        )
        
        await safe_edit_message(
            message=query.message,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_products_list_keyboard(products, category_id)
        )
    except Exception as e:
        logger.error(f"Error in admin_products_category_handler: {e}", exc_info=True)
        await query.answer("Произошла ошибка при загрузке товаров", show_alert=True)

@dp.callback_query(F.data.startswith("create_product:"))
async def create_product_handler(
    callback: types.CallbackQuery,
    state: FSMContext
) -> None:
    """Создание нового товара"""
    try:
        if not await check_admin_access(callback.from_user.id, callback):
            return
        
        category_id = callback.data.split(':')[1]
        logger.info(f"Product creation started in category {category_id} by user {callback.from_user.id}")
        
        await safe_clear_state(state)
        await state.set_state(ProductForm.name)
        await state.update_data(category_id=category_id)
        
        await safe_edit_message(
            message=callback.message,
            text="✏️ Введите название нового товара:",
            reply_markup=get_cancel_keyboard("cancel_product_creation")
        )
    except Exception as e:
        logger.error(f"Error in create_product_handler: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при создании товара", show_alert=True)

@dp.callback_query(F.data.startswith("admin_product_edit:"))
async def admin_product_edit_handler(
    query: types.CallbackQuery,
    state: FSMContext
) -> None:
    """Редактирование товара"""
    try:
        if not await check_admin_access(query.from_user.id, query):
            return
        
        product_id = query.data.split(':')[1]
        logger.info(f"Admin editing product {product_id} by user {query.from_user.id}")
        
        product = next((p for p in db.get_all_products() if p['id'] == product_id), None)
        if not product:
            logger.error(f"Product {product_id} not found")
            await query.answer("Товар не найден", show_alert=True)
            return
        
        await state.set_state(ProductForm.edit_name)
        await state.update_data(product_id=product_id)
        
        await safe_edit_message(
            message=query.message,
            text=f"✏️ Редактирование товара\n\nТекущее название: {product['name']}\n\nВведите новое название:",
            reply_markup=get_cancel_keyboard("cancel_product_edit")
        )
    except Exception as e:
        logger.error(f"Error in admin_product_edit_handler: {e}", exc_info=True)
        await query.answer("Произошла ошибка при редактировании товара", show_alert=True)

@dp.callback_query(F.data.startswith("admin_product_delete:"))
async def admin_product_delete_handler(
    query: types.CallbackQuery,
    state: FSMContext
) -> None:
    """Удаление товара"""
    try:
        if not await check_admin_access(query.from_user.id, query):
            return
        
        product_id = query.data.split(':')[1]
        logger.info(f"Admin deleting product {product_id} by user {query.from_user.id}")
        
        product = next((p for p in db.get_all_products() if p['id'] == product_id), None)
        if not product:
            logger.error(f"Product {product_id} not found")
            await query.answer("Товар не найден", show_alert=True)
            return
        
        await state.set_state(ProductForm.confirm_delete)
        await state.update_data(product_id=product_id)
        
        await safe_edit_message(
            message=query.message,
            text=f"⚠️ Подтверждение удаления\n\nВы уверены, что хотите удалить товар '{product['name']}'?",
            reply_markup=get_confirm_keyboard(
                confirm_callback=f"confirm_product_delete:{product_id}",
                cancel_callback="cancel_product_delete"
            )
        )
    except Exception as e:
        logger.error(f"Error in admin_product_delete_handler: {e}", exc_info=True)
        await query.answer("Произошла ошибка при удалении товара", show_alert=True)

# ===== ТЕСТЫ =====
@dp.callback_query(F.data == "admin_tests")
async def admin_tests_handler(query: types.CallbackQuery, state: FSMContext) -> None:
    """Управление тестами"""
    try:
        if not await check_admin_access(query.from_user.id, query):
            return
        
        logger.info(f"Tests menu opened by user {query.from_user.id}")
        await safe_clear_state(state)
        
        tests = db.get_tests_list()
        buttons = []
        
        # Add test buttons
        for test in tests:
            buttons.append([
                types.InlineKeyboardButton(
                    text=f"✏️ {test['title']}", 
                    callback_data=f"test_edit:{test['id']}"
                )
            ])
        
        # Add create and back buttons
        buttons.extend([
            [types.InlineKeyboardButton(text="➕ Создать тест", callback_data="create_test")],
            [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin")]
        ])
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
        
        text = "📝 <b>Управление тестами</b>\n\nВыберите тест для редактирования или создайте новый:"
        if not tests:
            text = "📝 <b>Управление тестами</b>\n\nТесты пока не созданы. Создайте первый тест:"
        
        await query.answer()
        await safe_edit_message(
            message=query.message,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in admin_tests_handler: {e}", exc_info=True)
        await query.answer("Произошла ошибка при загрузке тестов", show_alert=True)

@dp.callback_query(F.data.startswith("admin_test_edit:"))
async def admin_test_edit_handler(
    query: types.CallbackQuery,
    state: FSMContext
) -> None:
    """Редактирование теста"""
    try:
        if not await check_admin_access(query.from_user.id, query):
            return
        
        test_id = query.data.split(':')[1]
        logger.info(f"Admin editing test {test_id} by user {query.from_user.id}")
        
        test = next((t for t in db.get_tests_list() if t['id'] == test_id), None)
        if not test:
            logger.error(f"Test {test_id} not found")
            await query.answer("Тест не найден", show_alert=True)
            return
        
        await state.set_state(TestForm.edit_title)
        await state.update_data(test_id=test_id)
        
        await safe_edit_message(
            message=query.message,
            text=f"✏️ Редактирование теста\n\nТекущее название: {test['title']}\n\nВведите новое название:",
            reply_markup=get_cancel_keyboard("cancel_test_edit")
        )
    except Exception as e:
        logger.error(f"Error in admin_test_edit_handler: {e}", exc_info=True)
        await query.answer("Произошла ошибка при редактировании теста", show_alert=True)

@dp.callback_query(F.data.startswith("admin_test_delete:"))
async def admin_test_delete_handler(
    query: types.CallbackQuery,
    state: FSMContext
) -> None:
    """Удаление теста"""
    try:
        if not await check_admin_access(query.from_user.id, query):
            return
        
        test_id = query.data.split(':')[1]
        logger.info(f"Admin deleting test {test_id} by user {query.from_user.id}")
        
        test = next((t for t in db.get_tests_list() if t['id'] == test_id), None)
        if not test:
            logger.error(f"Test {test_id} not found")
            await query.answer("Тест не найден", show_alert=True)
            return
        
        await state.set_state(TestForm.confirm_delete)
        await state.update_data(test_id=test_id)
        
        await safe_edit_message(
            message=query.message,
            text=f"⚠️ Подтверждение удаления\n\nВы уверены, что хотите удалить тест '{test['title']}'?",
            reply_markup=get_confirm_keyboard(
                confirm_callback=f"confirm_test_delete:{test_id}",
                cancel_callback="cancel_test_delete"
            )
        )
    except Exception as e:
        logger.error(f"Error in admin_test_delete_handler: {e}", exc_info=True)
        await query.answer("Произошла ошибка при удалении теста", show_alert=True)

@dp.callback_query(F.data == "create_test")
async def create_test_handler(
    query: types.CallbackQuery,
    state: FSMContext
) -> None:
    """Создание нового теста"""
    try:
        if not await check_admin_access(query.from_user.id, query):
            return
        
        logger.info(f"Test creation started by user {query.from_user.id}")
        await state.set_state(TestForm.title)
        
        await safe_edit_message(
            message=query.message,
            text="✏️ Введите название нового теста:",
            reply_markup=get_cancel_keyboard("cancel_test_creation")
        )
    except Exception as e:
        logger.error(f"Error in create_test_handler: {e}", exc_info=True)
        await query.answer("Произошла ошибка при создании теста", show_alert=True)

# ===== СТАТИСТИКА =====
@dp.callback_query(F.data == "admin_stats")
async def admin_stats_handler(query: types.CallbackQuery, state: FSMContext) -> None:
    """Просмотр статистики"""
    try:
        if not await check_admin_access(query.from_user.id, query):
            return
        
        logger.info(f"Stats menu opened by user {query.from_user.id}")
        await safe_clear_state(state)
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_stats_users"),
                types.InlineKeyboardButton(text="📝 Тесты", callback_data="admin_stats_tests")
            ],
            [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin")]
        ])
        
        text = "📊 <b>Статистика</b>\n\nВыберите тип статистики:"
        
        await query.answer()
        await safe_edit_message(
            message=query.message,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in admin_stats_handler: {e}", exc_info=True)
        await query.answer("Произошла ошибка при загрузке статистики", show_alert=True)

# ===== ПОИСК ТОВАРОВ =====
@dp.callback_query(F.data == "admin_search_products")
async def admin_search_products_handler(
    query: types.CallbackQuery,
    state: FSMContext
) -> None:
    """Поиск товаров"""
    if not await check_admin_access(query.from_user.id, query):
        return
    
    await safe_clear_state(state)  # Clear any existing state first
    await state.set_state(ProductForm.search)
    await safe_edit_message(
        message=query.message,
        text="🔍 Введите поисковый запрос:",
        reply_markup=get_cancel_keyboard("cancel_search")
    )

@dp.message(ProductForm.search)
async def process_product_search(
    message: types.Message,
    state: FSMContext
) -> None:
    """Обработка поискового запроса"""
    if not await check_admin_access(message.from_user.id):
        return
    
    query_text = message.text.strip()
    if not query_text:
        await message.answer("❌ Поисковый запрос не может быть пустым")
        return
    
    products = db.search_products(query_text)
    if not products:
        await message.answer("❌ Товары не найдены")
        await safe_clear_state(state)
        return
    
    text = f"🔍 <b>Результаты поиска</b>\n\nНайдено товаров: {len(products)}\n\n"
    for product in products:
        text += f"• {product['name']} (ID: {product['id']})\n"
    
    await message.answer(text, parse_mode=ParseMode.HTML)
    await safe_clear_state(state)

@dp.message(CategoryForm.name)
async def process_name(message: Message, state: FSMContext):
    """Обработка ввода названия категории"""
    if not await check_admin_access(message.from_user.id):
        return
    
    name = message.text.strip()
    if not name:
        await message.answer("❌ Название категории не может быть пустым")
        return
    
    try:
        db.add_category(name)
        await message.answer(f"✅ Категория '{name}' успешно создана")
    except Exception as e:
        logger.error(f"Failed to create category: {e}")
        await message.answer("❌ Ошибка при создании категории")
    
    await safe_clear_state(state)

# ===== ОТМЕНА ДЕЙСТВИЙ =====
@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_handler(
    query: types.CallbackQuery,
    state: FSMContext
) -> None:
    """Отмена текущего действия"""
    if not await check_admin_access(query.from_user.id, query):
        return
    
    await safe_clear_state(state)
    await query.answer("❌ Действие отменено")
    await send_admin_menu(query)

# ===== АДМИНИСТРАТИВНЫЕ ОБРАБОТЧИКИ =====
class AdminStates(StatesGroup):
    """States for admin interactions."""
    managing_users = State()
    managing_catalog = State()
    managing_tests = State()
    viewing_stats = State()
    managing_settings = State()
    adding_category = State()
    editing_category = State()
    adding_product = State()
    editing_product = State()
    adding_test = State()
    editing_test = State()
    adding_question = State()
    editing_question = State()

def is_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    return user_id in ADMIN_IDS

@dp.message(Command("admin"))
@dp.message(F.text == "⚙️ Управление")
async def show_admin_panel(message: Message, state: FSMContext):
    """Show admin control panel."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к панели управления.")
        return
    
    try:
        await message.answer(
            "⚙️ Панель управления\n\n"
            "Выберите раздел для управления:",
            reply_markup=get_admin_control_keyboard()
        )
        await state.set_state(AdminStates.managing_settings)
        
        # Track metrics
        metrics_collector.increment_message_count()
        
    except Exception as e:
        logger.error(f"Error showing admin panel: {e}")
        await message.answer(
            "😔 Произошла ошибка при загрузке панели управления. Попробуйте позже.",
            reply_markup=get_back_keyboard()
        )

@dp.callback_query(F.data == "admin_users")
async def manage_users(callback: CallbackQuery, state: FSMContext):
    """Show user management interface."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return
    
    try:
        # Get db_pool from bot_data
        db_pool = callback.bot.bot_data.get('db_pool')
        if not db_pool:
            logger.error("Database pool not available in handler context.")
            await callback.answer("Database connection not available.")
            return

        # Get user statistics
        total_users = await db_pool.fetchone(
            "SELECT COUNT(*) as count FROM users"
        )
        active_users = await db_pool.fetchone(
            """
            SELECT COUNT(DISTINCT user_id) as count 
            FROM user_activity 
            WHERE last_active > ?
            """,
            (datetime.now() - timedelta(days=7),)
        )
        test_stats = await db_pool.fetchone(
            """
            SELECT 
                COUNT(DISTINCT user_id) as users_with_tests,
                AVG(score) as avg_score
            FROM test_attempts
            WHERE completed_at IS NOT NULL
            """
        )
        
        # Format statistics message
        stats_text = "👥 Управление пользователями\n\n"
        stats_text += f"📊 Статистика:\n"
        stats_text += f"• Всего пользователей: {total_users['count']}\n"
        stats_text += f"• Активных за неделю: {active_users['count']}\n"
        if test_stats['users_with_tests']:
            stats_text += f"• Прошли тесты: {test_stats['users_with_tests']}\n"
            stats_text += f"• Средний балл: {test_stats['avg_score']:.1f}%\n"
        
        # Get recent user activity
        recent_activity = await db_pool.fetchall(
            """
            SELECT u.*, ua.last_active, ua.message_count
            FROM users u
            JOIN user_activity ua ON u.id = ua.user_id
            ORDER BY ua.last_active DESC
            LIMIT 5
            """
        )
        
        if recent_activity:
            stats_text += "\n🔄 Последняя активность:\n"
            for user in recent_activity:
                stats_text += f"• {user['username'] or user['first_name']}\n"
                stats_text += f"  📝 Сообщений: {user['message_count']}\n"
                stats_text += f"  ⏱ Последняя активность: {user['last_active']}\n"
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_admin_control_keyboard()
        )
        await state.set_state(AdminStates.managing_users)
        
        # Track metrics
        metrics_collector.increment_message_count()
        
    except Exception as e:
        logger.error(f"Error managing users: {e}")
        await callback.message.edit_text(
            "😔 Произошла ошибка при загрузке данных пользователей. Попробуйте позже.",
            reply_markup=get_back_keyboard()
        )

@dp.callback_query(F.data == "admin_catalog")
async def manage_catalog(callback: CallbackQuery, state: FSMContext):
    """Show catalog management interface."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return
    
    try:
        # Get db_pool from bot_data
        db_pool = callback.bot.bot_data.get('db_pool')
        if not db_pool:
            logger.error("Database pool not available in handler context.")
            await callback.answer("Database connection not available.")
            return

        # Get catalog statistics
        categories_count = await db_pool.fetchone(
            "SELECT COUNT(*) as count FROM categories WHERE is_active = 1"
        )
        products_count = await db_pool.fetchone(
            "SELECT COUNT(*) as count FROM products WHERE is_active = 1"
        )
        
        # Format statistics message
        stats_text = "📚 Управление каталогом\n\n"
        stats_text += f"📊 Статистика:\n"
        stats_text += f"• Категорий: {categories_count['count']}\n"
        stats_text += f"• Товаров: {products_count['count']}\n"
        
        # Get recent additions
        recent_products = await db_pool.fetchall(
            """
            SELECT p.*, c.name as category_name
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE p.is_active = 1
            ORDER BY p.created_at DESC
            LIMIT 5
            """
        )
        
        if recent_products:
            stats_text += "\n🆕 Последние добавленные товары:\n"
            for product in recent_products:
                stats_text += f"• {product['name']}\n"
                stats_text += f"  📚 Категория: {product['category_name']}\n"
                if product['price']:
                    stats_text += f"  💰 {product['price']} руб.\n"
        
        # Add management options
        stats_text += "\n⚙️ Действия:\n"
        stats_text += "• Добавить категорию\n"
        stats_text += "• Добавить товар\n"
        stats_text += "• Редактировать категории\n"
        stats_text += "• Редактировать товары\n"
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_admin_control_keyboard()
        )
        await state.set_state(AdminStates.managing_catalog)
        
        # Track metrics
        metrics_collector.increment_message_count()
        
    except Exception as e:
        logger.error(f"Error managing catalog: {e}")
        await callback.message.edit_text(
            "😔 Произошла ошибка при загрузке данных каталога. Попробуйте позже.",
            reply_markup=get_back_keyboard()
        )

@dp.callback_query(F.data == "admin_tests")
async def manage_tests(callback: CallbackQuery, state: FSMContext):
    """Show test management interface."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return
    
    try:
        # Get db_pool from bot_data
        db_pool = callback.bot.bot_data.get('db_pool')
        if not db_pool:
            logger.error("Database pool not available in handler context.")
            await callback.answer("Database connection not available.")
            return

        # Get test statistics
        tests_count = await db_pool.fetchone(
            "SELECT COUNT(*) as count FROM tests WHERE is_active = 1"
        )
        questions_count = await db_pool.fetchone(
            "SELECT COUNT(*) as count FROM test_questions"
        )
        attempts_count = await db_pool.fetchone(
            """
            SELECT 
                COUNT(*) as total_attempts,
                COUNT(DISTINCT user_id) as unique_users,
                AVG(score) as avg_score
            FROM test_attempts
            WHERE completed_at IS NOT NULL
            """
        )
        
        # Format statistics message
        stats_text = "📝 Управление тестами\n\n"
        stats_text += f"📊 Статистика:\n"
        stats_text += f"• Активных тестов: {tests_count['count']}\n"
        stats_text += f"• Вопросов: {questions_count['count']}\n"
        if attempts_count['total_attempts']:
            stats_text += f"• Всего попыток: {attempts_count['total_attempts']}\n"
            stats_text += f"• Уникальных пользователей: {attempts_count['unique_users']}\n"
            stats_text += f"• Средний балл: {attempts_count['avg_score']:.1f}%\n"
        
        # Get recent test results
        recent_results = await db_pool.fetchall(
            """
            SELECT 
                t.name as test_name,
                u.username,
                ta.score,
                ta.completed_at
            FROM test_attempts ta
            JOIN tests t ON ta.test_id = t.id
            JOIN users u ON ta.user_id = u.id
            WHERE ta.completed_at IS NOT NULL
            ORDER BY ta.completed_at DESC
            LIMIT 5
            """
        )
        
        if recent_results:
            stats_text += "\n📊 Последние результаты:\n"
            for result in recent_results:
                stats_text += f"• {result['test_name']}\n"
                stats_text += f"  👤 {result['username']}\n"
                stats_text += f"  📈 {result['score']}%\n"
                stats_text += f"  ⏱ {result['completed_at']}\n"
        
        # Add management options
        stats_text += "\n⚙️ Действия:\n"
        stats_text += "• Добавить тест\n"
        stats_text += "• Редактировать тесты\n"
        stats_text += "• Просмотр результатов\n"
        stats_text += "• Экспорт статистики\n"
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_admin_control_keyboard()
        )
        await state.set_state(AdminStates.managing_tests)
        
        # Track metrics
        metrics_collector.increment_message_count()
        
    except Exception as e:
        logger.error(f"Error managing tests: {e}")
        await callback.message.edit_text(
            "😔 Произошла ошибка при загрузке данных тестов. Попробуйте позже.",
            reply_markup=get_back_keyboard()
        )

@dp.callback_query(F.data == "admin_stats")
async def view_stats(callback: CallbackQuery, state: FSMContext):
    """Show detailed bot statistics."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return
    
    try:
        # Get db_pool from bot_data
        db_pool = callback.bot.bot_data.get('db_pool')
        if not db_pool:
            logger.error("Database pool not available in handler context.")
            await callback.answer("Database connection not available.")
            return

        # Get general statistics
        users_count = await db_pool.fetchone(
            "SELECT COUNT(*) as count FROM users"
        )
        messages_count = await db_pool.fetchone(
            "SELECT SUM(message_count) as count FROM user_activity"
        )
        tests_count = await db_pool.fetchone(
            "SELECT COUNT(*) as count FROM test_attempts WHERE completed_at IS NOT NULL"
        )
        
        # Get activity statistics
        daily_activity = await db_pool.fetchall(
            """
            SELECT 
                DATE(last_active) as date,
                COUNT(DISTINCT user_id) as active_users,
                SUM(message_count) as messages
            FROM user_activity
            WHERE last_active > ?
            GROUP BY DATE(last_active)
            ORDER BY date DESC
            LIMIT 7
            """,
            (datetime.now() - timedelta(days=7),)
        )
        
        # Format statistics message
        stats_text = "📊 Статистика бота\n\n"
        stats_text += f"📈 Общая статистика:\n"
        stats_text += f"• Пользователей: {users_count['count']}\n"
        stats_text += f"• Сообщений: {messages_count['count'] or 0}\n"
        stats_text += f"• Пройдено тестов: {tests_count['count']}\n"
        
        if daily_activity:
            stats_text += "\n📅 Активность за неделю:\n"
            for day in daily_activity:
                stats_text += f"• {day['date']}:\n"
                stats_text += f"  👥 Активных: {day['active_users']}\n"
                stats_text += f"  💬 Сообщений: {day['messages']}\n"
        
        # Get system metrics
        metrics = metrics_collector.get_latest_metrics()
        if metrics:
            stats_text += "\n💻 Системные метрики:\n"
            stats_text += f"• CPU: {metrics['cpu_percent']}%\n"
            stats_text += f"• Память: {metrics['memory_percent']}%\n"
            stats_text += f"• Диск: {metrics['disk_percent']}%\n"
            stats_text += f"• Аптайм: {metrics['uptime']}\n"
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_admin_control_keyboard()
        )
        await state.set_state(AdminStates.viewing_stats)
        
        # Track metrics
        metrics_collector.increment_message_count()
        
    except Exception as e:
        logger.error(f"Error viewing stats: {e}")
        await callback.message.edit_text(
            "😔 Произошла ошибка при загрузке статистики. Попробуйте позже.",
            reply_markup=get_back_keyboard()
        )

@dp.callback_query(F.data == "admin_settings")
async def manage_settings(callback: CallbackQuery, state: FSMContext):
    """Show bot settings management interface."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return
    
    try:
        # Get current settings
        settings = await db_pool.fetchall(
            "SELECT * FROM settings"
        )
        
        # Format settings message
        settings_text = "⚙️ Управление настройками\n\n"
        settings_text += "📋 Текущие настройки:\n"
        
        for setting in settings:
            settings_text += f"• {setting['name']}: {setting['value']}\n"
            if setting['description']:
                settings_text += f"  {setting['description']}\n"
        
        # Add management options
        settings_text += "\n⚙️ Действия:\n"
        settings_text += "• Изменить настройки\n"
        settings_text += "• Сбросить настройки\n"
        settings_text += "• Экспорт настроек\n"
        settings_text += "• Импорт настроек\n"
        
        await callback.message.edit_text(
            settings_text,
            reply_markup=get_admin_control_keyboard()
        )
        await state.set_state(AdminStates.managing_settings)
        
        # Track metrics
        metrics_collector.increment_message_count()
        
    except Exception as e:
        logger.error(f"Error managing settings: {e}")
        await callback.message.edit_text(
            "😔 Произошла ошибка при загрузке настроек. Попробуйте позже.",
            reply_markup=get_back_keyboard()
        )

@dp.callback_query(F.data == "back_to_main")
async def back_to_admin_panel(callback: CallbackQuery, state: FSMContext):
    """Return to admin panel."""
    await state.clear()
    await show_admin_panel(callback.message, state)

async def setup_admin_handlers(dispatcher):
    """Placeholder function to satisfy import requirements."""
    pass

__all__ = [
    'admin_handler',
    'admin_categories_handler',
    'create_category_handler',
    'admin_category_edit_handler',
    'admin_category_delete_handler',
    'admin_products_handler',
    'admin_products_category_handler',
    'create_product_handler',
    'admin_product_edit_handler',
    'admin_product_delete_handler',
    'admin_tests_handler',
    'admin_test_edit_handler',
    'admin_test_delete_handler',
    'create_test_handler',
    'admin_stats_handler',
    'admin_search_products_handler',
    'show_admin_panel',
    'manage_users',
    'manage_catalog',
    'manage_tests',
    'view_stats',
    'manage_settings',
    'back_to_admin_panel',
    'setup_admin_handlers'
]
