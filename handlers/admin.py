from aiogram import F, types
from aiogram.types import Message
from aiogram.filters import Command
import uuid
import logging
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from utils.message_utils import safe_edit_message
from sqlite_db import db  # Import the database instance
from config import ADMIN_USER_IDS
from utils.keyboards import (
    get_admin_keyboard, get_admin_categories_keyboard,
    get_admin_products_keyboard, get_admin_products_list_keyboard,
    get_admin_tests_keyboard, get_admin_stats_keyboard,
    get_cancel_keyboard, get_confirmation_keyboard
)
from dispatcher import dp
from states import CategoryForm, ProductForm, TestForm

logger = logging.getLogger(__name__)

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
async def check_admin_access(user_id: int, query: types.CallbackQuery = None) -> bool:
    """Проверяет права администратора"""
    if user_id not in ADMIN_USER_IDS:  # Updated to use ADMIN_USER_IDS
        msg = "⛔ У вас нет доступа к административной панели"
        if query:
            await query.answer(msg)
        return False
    return True

async def admin_check_middleware(handler, event, data):
    if event.from_user.id not in ADMIN_USER_IDS:
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
            reply_markup=get_confirmation_keyboard(
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
            reply_markup=get_confirmation_keyboard(
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
            reply_markup=get_confirmation_keyboard(
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
    'admin_search_products_handler'
]
