import logging
import os
import sys
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.enums import ParseMode

# Import local modules
from config import (
    BOT_TOKEN, WEBAPP_HOST, WEBAPP_PORT, WEBHOOK_URL, WEBHOOK_PATH,
    validate_config, IS_PRODUCTION, ADMIN_IDS
)
from logging_config import setup_logging
from sqlite_db import init_db, close_db
from middleware import setup_middleware
from dispatcher import setup_handlers
from user_management import setup_user_handlers
from admin_handlers import setup_admin_handlers
from product_management import setup_product_handlers
from category_management import setup_category_handlers
from test_management import setup_test_handlers

# Setup logging
logger = setup_logging()
logger.info("[BOOT] main.py started")

# Validate configuration
try:
    validate_config()
except ValueError as e:
    logger.error(f"[ERROR] Configuration validation failed: {e}")
    sys.exit(1)

# Create bot and dispatcher
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Setup middleware
setup_middleware(dp)

# Setup handlers
setup_handlers(dp)
setup_user_handlers(dp)
setup_admin_handlers(dp)
setup_product_handlers(dp)
setup_category_handlers(dp)
setup_test_handlers(dp)

# Basic command handlers
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS
    
    welcome_text = (
        "👋 Добро пожаловать в Корпоративную Базу Знаний!\n\n"
        "Я помогу вам изучить нашу продукцию и пройти тестирование.\n\n"
    )
    
    if is_admin:
        welcome_text += (
            "🔐 Вы авторизованы как администратор.\n"
            "Используйте /admin для доступа к панели управления."
        )
    else:
        welcome_text += (
            "📚 Доступные команды:\n"
            "/catalog - Просмотр каталога продукции\n"
            "/search - Поиск по базе знаний\n"
            "/tests - Доступные тесты\n"
            "/help - Справка по использованию бота"
        )
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Каталог"), KeyboardButton(text="🔍 Поиск")],
            [KeyboardButton(text="📝 Тесты"), KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True
    )
    
    if is_admin:
        keyboard.keyboard.append([KeyboardButton(text="⚙️ Панель управления")])
    
    await message.answer(welcome_text, reply_markup=keyboard)

@dp.message(Command("help"))
async def help_handler(message: types.Message):
    help_text = (
        "📚 <b>Справка по использованию бота</b>\n\n"
        "Основные команды:\n"
        "/start - Начать работу с ботом\n"
        "/catalog - Просмотр каталога продукции\n"
        "/search - Поиск по базе знаний\n"
        "/tests - Доступные тесты\n"
        "/help - Показать эту справку\n\n"
        "Для поиска информации используйте команду /search\n"
        "Для прохождения тестов используйте команду /tests\n"
        "Для просмотра каталога используйте команду /catalog"
    )
    
    if message.from_user.id in ADMIN_IDS:
        help_text += "\n\n<b>Команды администратора:</b>\n"
        help_text += "/admin - Панель управления\n"
        help_text += "/stats - Статистика использования\n"
    
    await message.answer(help_text)

# Create aiohttp app
app = web.Application()

# Health check endpoint
async def health(request):
    logger.info("[HTTP] /health requested")
    return web.Response(text="OK")
app.router.add_get("/health", health)

# Root endpoint
async def root(request):
    logger.info("[HTTP] / requested")
    return web.Response(text="Bot server is running")
app.router.add_get("/", root)

# Webhook handler
async def webhook_handler(request):
    logger.info("[HTTP] /webhook POST received")
    try:
        update = types.Update.model_validate(await request.json())
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.error(f"[ERROR] Webhook handler: {e}", exc_info=True)
    return web.Response(text="OK")
app.router.add_post(WEBHOOK_PATH, webhook_handler)

# Startup
async def on_startup(app):
    logger.info("[STARTUP] Initializing application...")
    
    # Initialize database
    await init_db()
    
    if IS_PRODUCTION:
        logger.info("[STARTUP] Setting webhook for production mode...")
        await bot.set_webhook(WEBHOOK_URL)
        logger.info(f"[STARTUP] Webhook set to {WEBHOOK_URL}")
    else:
        logger.info("[STARTUP] Running in development mode (polling)")
        # Start polling in development mode
        asyncio.create_task(dp.start_polling(bot))

app.on_startup.append(on_startup)

# Shutdown
async def on_shutdown(app):
    logger.info("[SHUTDOWN] Shutting down application...")
    
    if IS_PRODUCTION:
        await bot.delete_webhook()
    
    await close_db()
    await bot.session.close()
    
    logger.info("[SHUTDOWN] Application shutdown complete")

app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    if IS_PRODUCTION:
        logger.info("[MAIN] Starting web server in production mode...")
        web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)
    else:
        logger.info("[MAIN] Starting bot in development mode (polling)...")
        asyncio.run(dp.start_polling(bot))
