
from aiogram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

import firebase_db
from config import ADMIN_IDS
from utils.keyboards import get_admin_keyboard, get_admin_categories_keyboard, get_admin_products_keyboard, get_admin_products_list_keyboard, get_admin_tests_keyboard, get_admin_stats_keyboard

# Определяем состояния для ConversationHandler
(CATEGORY_NAME, CATEGORY_DESCRIPTION, CATEGORY_IMAGE,
 PRODUCT_NAME, PRODUCT_CATEGORY, PRODUCT_DESCRIPTION, PRODUCT_PRICE, PRODUCT_STORAGE, PRODUCT_IMAGES, PRODUCT_VIDEO,
 TEST_TITLE, TEST_DESCRIPTION, TEST_CATEGORY, TEST_QUESTIONS, TEST_PASSING_SCORE) = range(15)

# Глобальные данные для администраторских операций
admin_data = {}

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для административной панели"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Проверяем, является ли пользователь администратором
    if user_id not in ADMIN_IDS:
        if query:
            await query.answer("У вас нет доступа к административной панели.")
            return
        else:
            await update.message.reply_text("У вас нет доступа к административной панели.")
            return
    
    # Отображаем админ-панель
    admin_text = "🔧 <b>Административная панель</b>\n\n"
    admin_text += "Выберите раздел для управления:"
    
    if query:
        await query.answer()
        await query.edit_message_text(
            text=admin_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard()
        )
    else:
        await update.message.reply_text(
            text=admin_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard()
        )

async def admin_categories_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для управления категориями"""
    query = update.callback_query
    await query.answer()
    
    # Получаем категории из Firebase
    categories = firebase_db.get_categories()
    
    # Отображаем список категорий для управления
    await query.edit_message_text(
        text="📂 <b>Управление категориями</b>\n\nВыберите категорию для редактирования или создайте новую:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_admin_categories_keyboard(categories)
    )

async def admin_products_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для управления товарами"""
    query = update.callback_query
    await query.answer()
    
    # Проверяем, это выбор категории или возврат из категории
    parts = query.data.split(':')
    
    if len(parts) > 1 and parts[0] == 'admin_products_category':
        # Это выбор категории, отображаем товары для этой категории
        category_id = parts[1]
        
        # Получаем список товаров для этой категории
        products = firebase_db.get_products_by_category(category_id)
        
        # Получаем информацию о категории
        categories = firebase_db.get_categories()
        category = next((c for c in categories if c['id'] == category_id), None)
        category_name = category['name'] if category else "Категория"
        
        await query.edit_message_text(
            text=f"🍎 <b>Управление товарами</b>\n\nКатегория: {category_name}\n\nВыберите товар для редактирования или создайте новый:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_products_list_keyboard(products, category_id)
        )
    else:
        # Это основная страница управления товарами, отображаем список категорий
        categories = firebase_db.get_categories()
        
        await query.edit_message_text(
            text="🍎 <b>Управление товарами</b>\n\nВыберите категорию товаров:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_products_keyboard(categories)
        )

async def admin_tests_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для управления тестами"""
    query = update.callback_query
    await query.answer()
    
    # Получаем список всех тестов
    tests = firebase_db.get_tests_list()
    
    await query.edit_message_text(
        text="📝 <b>Управление тестами</b>\n\nВыберите тест для редактирования или создайте новый:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_admin_tests_keyboard(tests)
    )

async def admin_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для просмотра статистики"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    
    if len(parts) > 2 and parts[2] == 'users':
        # Статистика пользователей
        users = firebase_db.get_all_users()
        
        stats_text = "👥 <b>Статистика пользователей</b>\n\n"
        stats_text += f"Всего пользователей: {len(users)}\n"
        admin_count = sum(1 for user in users if user.get('is_admin'))
        stats_text += f"Администраторов: {admin_count}\n"
        stats_text += f"Обычных пользователей: {len(users) - admin_count}\n\n"
        
        # Добавляем список последних 10 активных пользователей
        active_users = sorted(users, key=lambda u: u.get('last_active', 0), reverse=True)[:10]
        if active_users:
            stats_text += "<b>Последние активные пользователи:</b>\n"
            for user in active_users:
                name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                username = f"@{user.get('username')}" if user.get('username') else "без username"
                stats_text += f"- {name} ({username})\n"
        
        await query.edit_message_text(
            text=stats_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_stats_keyboard()
        )
    
    elif len(parts) > 2 and parts[2] == 'tests':
        # Статистика тестов
        # Здесь мы бы получали статистику по тестам, но это требует дополнительной реализации
        # Вместо этого отображаем заглушку
        
        stats_text = "📝 <b>Статистика тестирования</b>\n\n"
        stats_text += "В разработке. Скоро здесь появится детальная статистика по прохождению тестов.\n"
        
        await query.edit_message_text(
            text=stats_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_stats_keyboard()
        )
    
    else:
        # Основная страница статистики
        await query.edit_message_text(
            text="📊 <b>Статистика</b>\n\nВыберите тип статистики для просмотра:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_stats_keyboard()
        )

# Здесь можно добавить дополнительные обработчики для создания и редактирования сущностей
# Например, add_category_handler, edit_product_handler и т.д.
# Они бы использовали ConversationHandler для управления диалогом с пользователем
