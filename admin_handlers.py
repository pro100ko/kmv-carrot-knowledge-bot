from typing import Optional, Dict, Any
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from admin_panel import (
    is_admin,
    get_admin_keyboard,
    get_categories_keyboard,
    get_products_keyboard,
    get_tests_keyboard,
    get_stats_keyboard,
    edit_message,
    format_admin_message,
    format_error_message,
    AdminCallback,
    AdminCategoryCallback,
    AdminProductCallback,
    AdminTestCallback,
    AdminStatsCallback
)
from logging_config import admin_logger
from sqlite_db import db

# Create router for admin handlers
router = Router()

# States for admin forms
class CategoryForm(StatesGroup):
    name = State()
    description = State()
    image = State()

class ProductForm(StatesGroup):
    category = State()
    name = State()
    description = State()
    price = State()
    images = State()

class TestForm(StatesGroup):
    title = State()
    description = State()
    passing_score = State()
    time_limit = State()
    questions = State()

# Command handlers
@router.message(Command("admin"))
async def admin_command(message: Message) -> None:
    """Handle /admin command"""
    if not is_admin(message.from_user.id):
        admin_logger.warning(
            f"Unauthorized admin access attempt by user {message.from_user.id}"
        )
        await message.answer(
            "У вас нет доступа к админ-панели.",
            parse_mode="HTML"
        )
        return
    
    admin_logger.info(f"Admin panel accessed by user {message.from_user.id}")
    
    text = format_admin_message(
        title="👨‍💼 Админ-панель",
        content=(
            "Добро пожаловать в админ-панель!\n\n"
            "Выберите раздел для управления:"
        )
    )
    
    await message.answer(text, reply_markup=get_admin_keyboard())

# Callback handlers
@router.callback_query(AdminCallback.filter(F.action == "main"))
async def admin_main_callback(callback: CallbackQuery) -> None:
    """Handle main admin panel callback"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    text = format_admin_message(
        title="👨‍💼 Админ-панель",
        content=(
            "Добро пожаловать в админ-панель!\n\n"
            "Выберите раздел для управления:"
        )
    )
    
    await edit_message(callback, text, get_admin_keyboard())

@router.callback_query(AdminCallback.filter(F.action == "categories"))
async def admin_categories_callback(callback: CallbackQuery) -> None:
    """Handle categories management callback"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    text = format_admin_message(
        title="📁 Управление категориями",
        content=(
            "Выберите категорию для редактирования или создайте новую.\n\n"
            "✅ - активная категория\n"
            "❌ - неактивная категория"
        )
    )
    
    await edit_message(callback, text, get_categories_keyboard())

@router.callback_query(AdminCallback.filter(F.action == "products"))
async def admin_products_callback(callback: CallbackQuery) -> None:
    """Handle products management callback"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    text = format_admin_message(
        title="📦 Управление товарами",
        content=(
            "Выберите товар для редактирования или создайте новый.\n\n"
            "✅ - активный товар\n"
            "❌ - неактивный товар"
        )
    )
    
    await edit_message(callback, text, get_products_keyboard())

@router.callback_query(AdminCallback.filter(F.action == "tests"))
async def admin_tests_callback(callback: CallbackQuery) -> None:
    """Handle tests management callback"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    text = format_admin_message(
        title="📝 Управление тестами",
        content=(
            "Выберите тест для редактирования или создайте новый.\n\n"
            "В скобках указано количество попыток прохождения."
        )
    )
    
    await edit_message(callback, text, get_tests_keyboard())

@router.callback_query(AdminCallback.filter(F.action == "stats"))
async def admin_stats_callback(callback: CallbackQuery) -> None:
    """Handle statistics callback"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    text = format_admin_message(
        title="📊 Статистика",
        content=(
            "Выберите раздел статистики для просмотра:\n\n"
            "👥 Пользователи - статистика по пользователям\n"
            "📊 Тесты - статистика по тестам\n"
            "📈 Продукты - статистика по товарам"
        )
    )
    
    await edit_message(callback, text, get_stats_keyboard())

# Category management callbacks
@router.callback_query(AdminCategoryCallback.filter(F.action == "list"))
async def category_list_callback(
    callback: CallbackQuery,
    callback_data: AdminCategoryCallback
) -> None:
    """Handle category list pagination"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    text = format_admin_message(
        title="📁 Управление категориями",
        content=(
            "Выберите категорию для редактирования или создайте новую.\n\n"
            "✅ - активная категория\n"
            "❌ - неактивная категория"
        )
    )
    
    await edit_message(
        callback,
        text,
        get_categories_keyboard(page=callback_data.page)
    )

@router.callback_query(AdminCategoryCallback.filter(F.action == "edit"))
async def category_edit_callback(
    callback: CallbackQuery,
    callback_data: AdminCategoryCallback,
    state: FSMContext
) -> None:
    """Handle category edit callback"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    try:
        category = db.get_category(callback_data.category_id)
        if not category:
            raise ValueError("Категория не найдена")
        
        text = format_admin_message(
            title=f"📁 Редактирование категории: {category['name']}",
            content=(
                f"<b>Название:</b> {category['name']}\n"
                f"<b>Описание:</b> {category['description'] or 'Нет'}\n"
                f"<b>Статус:</b> {'Активна' if category['is_active'] else 'Неактивна'}\n"
                f"<b>Товаров:</b> {len(db.get_products_by_category(category['id']))}\n\n"
                "Выберите действие:"
            )
        )
        
        # Create edit keyboard
        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text="✏️ Изменить название",
            callback_data=AdminCategoryCallback(
                action="edit_name",
                category_id=category['id']
            ).pack()
        )
        keyboard.button(
            text="📝 Изменить описание",
            callback_data=AdminCategoryCallback(
                action="edit_description",
                category_id=category['id']
            ).pack()
        )
        keyboard.button(
            text="🖼 Изменить изображение",
            callback_data=AdminCategoryCallback(
                action="edit_image",
                category_id=category['id']
            ).pack()
        )
        keyboard.button(
            text="✅ Активировать" if not category['is_active'] else "❌ Деактивировать",
            callback_data=AdminCategoryCallback(
                action="toggle_active",
                category_id=category['id']
            ).pack()
        )
        keyboard.button(
            text="🗑 Удалить",
            callback_data=AdminCategoryCallback(
                action="delete",
                category_id=category['id']
            ).pack()
        )
        keyboard.button(
            text="◀️ Назад к списку",
            callback_data=AdminCategoryCallback(action="list", page=1).pack()
        )
        keyboard.adjust(1)
        
        await edit_message(callback, text, keyboard.as_markup())
        
    except Exception as e:
        admin_logger.error(f"Error in category edit: {e}")
        await callback.answer(
            format_error_message(e),
            show_alert=True
        )

@router.callback_query(AdminCategoryCallback.filter(F.action == "create"))
async def category_create_callback(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """Handle category creation callback"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    text = format_admin_message(
        title="📁 Создание категории",
        content="Введите название новой категории:"
    )
    
    # Create cancel keyboard
    keyboard = InlineKeyboardBuilder()
    keyboard.button(
        text="❌ Отмена",
        callback_data=AdminCategoryCallback(action="list", page=1).pack()
    )
    
    await edit_message(callback, text, keyboard.as_markup())
    await state.set_state(CategoryForm.name)

# Product management callbacks
@router.callback_query(AdminProductCallback.filter(F.action == "list"))
async def product_list_callback(
    callback: CallbackQuery,
    callback_data: AdminProductCallback
) -> None:
    """Handle product list pagination"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    text = format_admin_message(
        title="📦 Управление товарами",
        content=(
            "Выберите товар для редактирования или создайте новый.\n\n"
            "✅ - активный товар\n"
            "❌ - неактивный товар"
        )
    )
    
    await edit_message(
        callback,
        text,
        get_products_keyboard(
            category_id=callback_data.category_id,
            page=callback_data.page
        )
    )

@router.callback_query(AdminProductCallback.filter(F.action == "edit"))
async def product_edit_callback(
    callback: CallbackQuery,
    callback_data: AdminProductCallback,
    state: FSMContext
) -> None:
    """Handle product edit callback"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    try:
        product = db.get_product(callback_data.product_id)
        if not product:
            raise ValueError("Товар не найден")
        
        category = db.get_category(product['category_id'])
        
        text = format_admin_message(
            title=f"📦 Редактирование товара: {product['name']}",
            content=(
                f"<b>Название:</b> {product['name']}\n"
                f"<b>Категория:</b> {category['name']}\n"
                f"<b>Описание:</b> {product['description'] or 'Нет'}\n"
                f"<b>Цена:</b> {product['price_info'] or 'Не указана'}\n"
                f"<b>Статус:</b> {'Активен' if product['is_active'] else 'Неактивен'}\n"
                f"<b>Изображений:</b> {len(product.get('images', []))}\n\n"
                "Выберите действие:"
            )
        )
        
        # Create edit keyboard
        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text="✏️ Изменить название",
            callback_data=AdminProductCallback(
                action="edit_name",
                product_id=product['id']
            ).pack()
        )
        keyboard.button(
            text="📝 Изменить описание",
            callback_data=AdminProductCallback(
                action="edit_description",
                product_id=product['id']
            ).pack()
        )
        keyboard.button(
            text="💰 Изменить цену",
            callback_data=AdminProductCallback(
                action="edit_price",
                product_id=product['id']
            ).pack()
        )
        keyboard.button(
            text="🖼 Управление изображениями",
            callback_data=AdminProductCallback(
                action="manage_images",
                product_id=product['id']
            ).pack()
        )
        keyboard.button(
            text="✅ Активировать" if not product['is_active'] else "❌ Деактивировать",
            callback_data=AdminProductCallback(
                action="toggle_active",
                product_id=product['id']
            ).pack()
        )
        keyboard.button(
            text="🗑 Удалить",
            callback_data=AdminProductCallback(
                action="delete",
                product_id=product['id']
            ).pack()
        )
        keyboard.button(
            text="◀️ Назад к списку",
            callback_data=AdminProductCallback(
                action="list",
                category_id=product['category_id'],
                page=1
            ).pack()
        )
        keyboard.adjust(1)
        
        await edit_message(callback, text, keyboard.as_markup())
        
    except Exception as e:
        admin_logger.error(f"Error in product edit: {e}")
        await callback.answer(
            format_error_message(e),
            show_alert=True
        )

@router.callback_query(AdminProductCallback.filter(F.action == "create"))
async def product_create_callback(
    callback: CallbackQuery,
    callback_data: AdminProductCallback,
    state: FSMContext
) -> None:
    """Handle product creation callback"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    # If category_id is provided, start with name
    if callback_data.category_id:
        await state.update_data(category_id=callback_data.category_id)
        text = format_admin_message(
            title="📦 Создание товара",
            content="Введите название нового товара:"
        )
        await state.set_state(ProductForm.name)
    else:
        # Otherwise, start with category selection
        text = format_admin_message(
            title="📦 Создание товара",
            content="Выберите категорию для нового товара:"
        )
        await state.set_state(ProductForm.category)
    
    # Create cancel keyboard
    keyboard = InlineKeyboardBuilder()
    keyboard.button(
        text="❌ Отмена",
        callback_data=AdminProductCallback(
            action="list",
            category_id=callback_data.category_id,
            page=1
        ).pack()
    )
    
    await edit_message(callback, text, keyboard.as_markup())

# Test management callbacks
@router.callback_query(AdminTestCallback.filter(F.action == "list"))
async def test_list_callback(
    callback: CallbackQuery,
    callback_data: AdminTestCallback
) -> None:
    """Handle test list pagination"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    text = format_admin_message(
        title="📝 Управление тестами",
        content=(
            "Выберите тест для редактирования или создайте новый.\n\n"
            "В скобках указано количество попыток прохождения."
        )
    )
    
    await edit_message(
        callback,
        text,
        get_tests_keyboard(page=callback_data.page)
    )

@router.callback_query(AdminTestCallback.filter(F.action == "edit"))
async def test_edit_callback(
    callback: CallbackQuery,
    callback_data: AdminTestCallback,
    state: FSMContext
) -> None:
    """Handle test edit callback"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    try:
        test = db.get_test(callback_data.test_id)
        if not test:
            raise ValueError("Тест не найден")
        
        # Get test statistics
        stats = db.get_test_stats(test['id'])
        
        text = format_admin_message(
            title=f"📝 Редактирование теста: {test['title']}",
            content=(
                f"<b>Название:</b> {test['title']}\n"
                f"<b>Описание:</b> {test['description'] or 'Нет'}\n"
                f"<b>Проходной балл:</b> {test['passing_score']}%\n"
                f"<b>Лимит времени:</b> {test['time_limit'] or 'Нет'}\n"
                f"<b>Вопросов:</b> {len(test['questions'])}\n\n"
                f"<b>Статистика:</b>\n"
                f"Попыток: {stats['attempts_count']}\n"
                f"Успешных: {stats['successful_attempts']}\n"
                f"Средний балл: {stats['average_score']:.1f}%\n\n"
                "Выберите действие:"
            )
        )
        
        # Create edit keyboard
        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text="✏️ Изменить название",
            callback_data=AdminTestCallback(
                action="edit_title",
                test_id=test['id']
            ).pack()
        )
        keyboard.button(
            text="📝 Изменить описание",
            callback_data=AdminTestCallback(
                action="edit_description",
                test_id=test['id']
            ).pack()
        )
        keyboard.button(
            text="📊 Изменить проходной балл",
            callback_data=AdminTestCallback(
                action="edit_passing_score",
                test_id=test['id']
            ).pack()
        )
        keyboard.button(
            text="⏱ Изменить лимит времени",
            callback_data=AdminTestCallback(
                action="edit_time_limit",
                test_id=test['id']
            ).pack()
        )
        keyboard.button(
            text="❓ Управление вопросами",
            callback_data=AdminTestCallback(
                action="manage_questions",
                test_id=test['id']
            ).pack()
        )
        keyboard.button(
            text="📊 Просмотр статистики",
            callback_data=AdminTestCallback(
                action="view_stats",
                test_id=test['id']
            ).pack()
        )
        keyboard.button(
            text="🗑 Удалить",
            callback_data=AdminTestCallback(
                action="delete",
                test_id=test['id']
            ).pack()
        )
        keyboard.button(
            text="◀️ Назад к списку",
            callback_data=AdminTestCallback(action="list", page=1).pack()
        )
        keyboard.adjust(1)
        
        await edit_message(callback, text, keyboard.as_markup())
        
    except Exception as e:
        admin_logger.error(f"Error in test edit: {e}")
        await callback.answer(
            format_error_message(e),
            show_alert=True
        )

@router.callback_query(AdminTestCallback.filter(F.action == "create"))
async def test_create_callback(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """Handle test creation callback"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    text = format_admin_message(
        title="📝 Создание теста",
        content="Введите название нового теста:"
    )
    
    # Create cancel keyboard
    keyboard = InlineKeyboardBuilder()
    keyboard.button(
        text="❌ Отмена",
        callback_data=AdminTestCallback(action="list", page=1).pack()
    )
    
    await edit_message(callback, text, keyboard.as_markup())
    await state.set_state(TestForm.title)

# Statistics callbacks
@router.callback_query(AdminStatsCallback.filter(F.action == "users"))
async def stats_users_callback(callback: CallbackQuery) -> None:
    """Handle users statistics callback"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    try:
        # Get user statistics
        stats = db.get_user_stats()
        
        text = format_admin_message(
            title="👥 Статистика пользователей",
            content=(
                f"<b>Всего пользователей:</b> {stats['total_users']}\n"
                f"<b>Активных пользователей:</b> {stats['active_users']}\n"
                f"<b>Новых пользователей за 24ч:</b> {stats['new_users_24h']}\n"
                f"<b>Новых пользователей за 7д:</b> {stats['new_users_7d']}\n"
                f"<b>Новых пользователей за 30д:</b> {stats['new_users_30d']}\n\n"
                "Выберите период для детальной статистики:"
            )
        )
        
        # Create period selection keyboard
        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text="📊 За 24 часа",
            callback_data=AdminStatsCallback(
                action="users",
                period="24h"
            ).pack()
        )
        keyboard.button(
            text="📊 За 7 дней",
            callback_data=AdminStatsCallback(
                action="users",
                period="7d"
            ).pack()
        )
        keyboard.button(
            text="📊 За 30 дней",
            callback_data=AdminStatsCallback(
                action="users",
                period="30d"
            ).pack()
        )
        keyboard.button(
            text="◀️ Назад к статистике",
            callback_data=AdminCallback(action="stats").pack()
        )
        keyboard.adjust(1)
        
        await edit_message(callback, text, keyboard.as_markup())
        
    except Exception as e:
        admin_logger.error(f"Error in users statistics: {e}")
        await callback.answer(
            format_error_message(e),
            show_alert=True
        )

@router.callback_query(AdminStatsCallback.filter(F.action == "tests"))
async def stats_tests_callback(callback: CallbackQuery) -> None:
    """Handle tests statistics callback"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    try:
        # Get test statistics
        tests = db.get_tests_list()
        total_attempts = sum(test['attempts_count'] for test in tests)
        successful_attempts = sum(
            test['attempts_count'] * test['success_rate'] / 100
            for test in tests
        )
        
        text = format_admin_message(
            title="📊 Статистика тестов",
            content=(
                f"<b>Всего тестов:</b> {len(tests)}\n"
                f"<b>Всего попыток:</b> {total_attempts}\n"
                f"<b>Успешных попыток:</b> {successful_attempts:.0f}\n"
                f"<b>Общий процент успешности:</b> "
                f"{(successful_attempts/total_attempts*100 if total_attempts else 0):.1f}%\n\n"
                "Выберите тест для детальной статистики:"
            )
        )
        
        # Create test selection keyboard
        keyboard = InlineKeyboardBuilder()
        for test in tests:
            keyboard.button(
                text=f"{test['title']} ({test['attempts_count']} попыток)",
                callback_data=AdminStatsCallback(
                    action="test_details",
                    target=str(test['id'])
                ).pack()
            )
        
        keyboard.button(
            text="◀️ Назад к статистике",
            callback_data=AdminCallback(action="stats").pack()
        )
        keyboard.adjust(1)
        
        await edit_message(callback, text, keyboard.as_markup())
        
    except Exception as e:
        admin_logger.error(f"Error in tests statistics: {e}")
        await callback.answer(
            format_error_message(e),
            show_alert=True
        )

@router.callback_query(AdminStatsCallback.filter(F.action == "products"))
async def stats_products_callback(callback: CallbackQuery) -> None:
    """Handle products statistics callback"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    try:
        # Get product statistics
        categories = db.get_categories()
        total_products = 0
        active_products = 0
        
        for category in categories:
            products = db.get_products_by_category(category['id'])
            total_products += len(products)
            active_products += sum(1 for p in products if p['is_active'])
        
        text = format_admin_message(
            title="📈 Статистика товаров",
            content=(
                f"<b>Всего категорий:</b> {len(categories)}\n"
                f"<b>Всего товаров:</b> {total_products}\n"
                f"<b>Активных товаров:</b> {active_products}\n"
                f"<b>Неактивных товаров:</b> {total_products - active_products}\n\n"
                "Выберите категорию для детальной статистики:"
            )
        )
        
        # Create category selection keyboard
        keyboard = InlineKeyboardBuilder()
        for category in categories:
            products = db.get_products_by_category(category['id'])
            keyboard.button(
                text=f"{category['name']} ({len(products)} товаров)",
                callback_data=AdminStatsCallback(
                    action="category_details",
                    target=str(category['id'])
                ).pack()
            )
        
        keyboard.button(
            text="◀️ Назад к статистике",
            callback_data=AdminCallback(action="stats").pack()
        )
        keyboard.adjust(1)
        
        await edit_message(callback, text, keyboard.as_markup())
        
    except Exception as e:
        admin_logger.error(f"Error in products statistics: {e}")
        await callback.answer(
            format_error_message(e),
            show_alert=True
        ) 