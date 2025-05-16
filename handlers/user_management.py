
from aiogram import types
from aiogram.enums import ParseMode

import sqlite_db import get_test_attempts
from config import ADMIN_IDS
from utils.keyboards import get_main_keyboard

async def start(update: types.Message | types.CallbackQuery, context=None) -> None:
    """Обработчик команды /start"""
    if isinstance(update, types.CallbackQuery):
        user = update.from_user
        chat_id = update.message.chat.id
    else:
        user = update.from_user
        chat_id = update.chat.id
    
    # Регистрируем пользователя
    user_data = {
        'telegram_id': user.id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'username': user.username,
    }
    sqlite_db.register_user(user_data)
    
    # Отправляем приветственное сообщение
    welcome_message = (
        f"👋 Добро пожаловать в бот «Морковка КМВ», {user.first_name}!\n\n"
        "🥕 Здесь вы найдете актуальную информацию о продуктах компании и сможете проверить свои знания."
    )
    
    # Проверяем, является ли пользователь администратором
    is_admin = user.id in ADMIN_IDS
    
    # Создаем клавиатуру для пользователя
    keyboard = get_main_keyboard(is_admin)
    
    # Отправляем сообщение с клавиатурой
    if isinstance(update, types.CallbackQuery):
        await update.message.answer(welcome_message, reply_markup=keyboard)
    else:
        await update.answer(welcome_message, reply_markup=keyboard)

async def get_test_attempts(user_id: int):
    """Получает попытки тестирования пользователя"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT t.title, ta.score, ta.max_score, ta.completed_at 
        FROM test_attempts ta
        JOIN tests t ON ta.test_id = t.id
        WHERE ta.user_id = ?
    """, (user_id,))
    
    attempts = cursor.fetchall()
    conn.close()
    return attempts

async def register_user_handler(update: types.Message, context=None) -> None:
    """Обработчик для регистрации пользователя и обработки неизвестных сообщений"""
    user = update.from_user
    
    # Регистрируем пользователя
    user_data = {
        'telegram_id': user.id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'username': user.username,
    }
    sqlite_db.register_user(user_data)
    
    # Обрабатываем текстовые команды для основных функций
    message_text = update.text
    
    if message_text == "🍎 База знаний":
        # Выполняем то же, что и при нажатии на кнопку knowledge_base
        await knowledge_base_handler(update, context)
    elif message_text == "📝 Тестирование":
        # Выполняем то же, что и при нажатии на кнопку testing
        await testing_handler(update, context)
    elif message_text == "⚙️ Админ панель" and user.id in ADMIN_IDS:
        # Выполняем то же, что и при нажатии на кнопку admin
        await admin_handler(update, context)
    else:
        # Для неизвестных команд отправляем основное меню
        is_admin = user.id in ADMIN_IDS
        keyboard = get_main_keyboard(is_admin)
        
        await update.answer("Выберите действие из меню:", reply_markup=keyboard)

# Импорт здесь, чтобы избежать циклических зависимостей
from handlers.knowledge_base import knowledge_base_handler
from handlers.testing import testing_handler
from handlers.admin import admin_handler
