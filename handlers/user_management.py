
from aiogram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import firebase_db
from config import ADMIN_IDS
from utils.keyboards import get_main_keyboard

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    
    # Регистрируем пользователя
    user_data = {
        'telegram_id': user.id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'username': user.username,
    }
    firebase_db.register_user(user_data)
    
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
    await update.message.reply_text(
        welcome_message,
        reply_markup=keyboard
    )

async def register_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для регистрации пользователя и обработки неизвестных сообщений"""
    user = update.effective_user
    
    # Регистрируем пользователя
    user_data = {
        'telegram_id': user.id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'username': user.username,
    }
    firebase_db.register_user(user_data)
    
    # Обрабатываем текстовые команды для основных функций
    message_text = update.message.text
    
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
        
        await update.message.reply_text(
            "Выберите действие из меню:",
            reply_markup=keyboard
        )

# Импорт здесь, чтобы избежать циклических зависимостей
from handlers.knowledge_base import knowledge_base_handler
from handlers.testing import testing_handler
from handlers.admin import admin_handler
