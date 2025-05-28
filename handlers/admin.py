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
    get_cancel_keyboard
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
@dp.message(Command("admin"))
@dp.callback_query(F.data == "admin")
async def admin_handler(
    update: types.Message | types.CallbackQuery,
    state: FSMContext
) -> None:
    """Главное меню админки"""
    user_id = update.from_user.id
    if not await check_admin_access(user_id, update if isinstance(update, types.CallbackQuery) else None):
        return
    
    await safe_clear_state(state)
    await send_admin_menu(update)

# ===== КАТЕГОРИИ =====
@dp.callback_query(F.data == "admin_categories")
async def admin_categories_handler(
    query: types.CallbackQuery,
    state: FSMContext
) -> None:
    """Управление категориями"""
    if not await check_admin_access(query.from_user.id, query):
        return
    
    await safe_clear_state(state)
    categories = db.get_categories()  # Use db instance
    
    await safe_edit_message(
        message=query.message,
        text="📂 <b>Управление категориями</b>\n\nВыберите категорию для редактирования или создайте новую:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_admin_categories_keyboard(categories)
    )

@dp.callback_query(F.data == "create_category")
async def create_category_handler(
    callback: types.CallbackQuery,
    state: FSMContext
) -> None:
    """Создание новой категории"""
    if not await check_admin_access(callback.from_user.id, callback):
        return
    
    await safe_clear_state(state)  # Clear any existing state first
    await state.set_state(CategoryForm.name)
    await safe_edit_message(
        message=callback.message,
        text="✏️ Введите название новой категории:",
        reply_markup=get_cancel_keyboard("cancel_category_creation")
    )

# ===== ТОВАРЫ =====
@dp.callback_query(F.data.startswith("admin_products"))
async def admin_products_handler(
    query: types.CallbackQuery,
    state: FSMContext
) -> None:
    """Управление товарами"""
    if not await check_admin_access(query.from_user.id, query):
        return
    
    await safe_clear_state(state)
    parts = query.data.split(':')
    
    if len(parts) > 1 and parts[0] == 'admin_products_category':
        # Показ товаров конкретной категории
        category_id = parts[1]
        products = db.get_products_by_category(category_id)
        category = next((c for c in db.get_categories() if c['id'] == category_id), None)
        
        text = (
            f"🍎 <b>Управление товарами</b>\n\n"
            f"Категория: {category['name'] if category else 'Неизвестная'}\n\n"
            f"Выберите товар для редактирования или создайте новый:"
        )
        
        await safe_edit_message(
            message=query.message,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_products_list_keyboard(products, category_id)
        )
    else:
        # Главное меню товаров
        categories = db.get_categories()
        await safe_edit_message(
            message=query.message,
            text="🍎 <b>Управление товарами</b>\n\nВыберите категорию товаров:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_products_keyboard(categories)
        )

@dp.callback_query(F.data == "create_product")
async def create_product_handler(
    callback: types.CallbackQuery,
    state: FSMContext
) -> None:
    """Создание нового товара"""
    if not await check_admin_access(callback.from_user.id, callback):
        return
    
    await safe_clear_state(state)  # Clear any existing state first
    await state.set_state(ProductForm.name)
    await safe_edit_message(
        message=callback.message,
        text="✏️ Введите название нового товара:",
        reply_markup=get_cancel_keyboard("cancel_product_creation")
    )

# ===== ТЕСТЫ =====
@dp.callback_query(F.data == "admin_tests")
async def admin_tests_handler(
    query: types.CallbackQuery,
    state: FSMContext
) -> None:
    """Управление тестами"""
    if not await check_admin_access(query.from_user.id, query):
        return
    
    await safe_clear_state(state)
    tests = db.get_tests_list()
    
    await safe_edit_message(
        message=query.message,
        text="📝 <b>Управление тестами</b>\n\nВыберите тест для редактирования или создайте новый:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_admin_tests_keyboard(tests)
    )

# ===== СТАТИСТИКА =====
@dp.callback_query(F.data.startswith("admin_stats"))
async def admin_stats_handler(
    query: types.CallbackQuery,
    state: FSMContext
) -> None:
    """Просмотр статистики"""
    if not await check_admin_access(query.from_user.id, query):
        return
    
    await safe_clear_state(state)
    parts = query.data.split('_')
    
    if len(parts) > 2:
        if parts[2] == 'users':
            # Статистика пользователей
            users = db.get_all_users()
            admin_count = sum(1 for u in users if u.get('is_admin'))
            
            text = (
                "👥 <b>Статистика пользователей</b>\n\n"
                f"Всего пользователей: {len(users)}\n"
                f"Администраторов: {admin_count}\n"
                f"Обычных пользователей: {len(users) - admin_count}\n\n"
                "<i>Детальная статистика в разработке...</i>"
            )
        elif parts[2] == 'tests':
            # Статистика тестов
            text = (
                "📝 <b>Статистика тестирования</b>\n\n"
                "<i>Функционал в разработке...</i>"
            )
        else:
            text = "📊 <b>Статистика</b>\n\nВыберите тип статистики:"
    else:
        text = "📊 <b>Статистика</b>\n\nВыберите тип статистики:"
    
    await safe_edit_message(
        message=query.message,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_admin_stats_keyboard()
    )

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
    'admin_products_handler',
    'create_product_handler',
    'admin_tests_handler',
    'admin_stats_handler',
    'admin_search_products_handler'
]
