import logging
import os
import sys
import time
import asyncio
from typing import Optional, Callable, Dict, Any

# Configure basic logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get port from environment immediately
PORT = int(os.getenv("PORT", os.getenv("WEBAPP_PORT", "8000")))
logger.info(f"Configured to use port {PORT}")

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Third-party imports
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.client.default import DefaultBotProperties
from aiogram.filters.command import Command, CommandStart
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from aiohttp import ClientSession
from aiogram.utils.callback_answer import CallbackAnswerMiddleware

# Local imports
from config import (
    BOT_TOKEN,
    WEBHOOK_URL,
    WEBHOOK_PATH,
    ENVIRONMENT,
    WEBHOOK_HOST,
    WEBHOOK_SSL_CERT,
    WEBAPP_HOST,
    ADMIN_IDS
)
from dispatcher import dp
from handlers import (
    admin,
    knowledge_base,
    testing,
    user_management
)
from handlers.admin import (
    admin_handler,
    admin_categories_handler,
    admin_products_handler,
    admin_tests_handler,
    admin_stats_handler,
    create_category_handler,
    create_product_handler
)
from handlers.knowledge_base import (
    knowledge_base_handler,
    category_handler,
    product_handler,
    search_handler
)
from handlers.testing import (
    testing_handler,
    test_selection_handler,
    test_question_handler,
    test_result_handler
)
from handlers.user_management import (
    start,
    register_user_handler
)
from logging_config import (
    app_logger,
    webhook_logger,
    setup_logging,
    cleanup_old_logs,
    get_logger
)
from middleware import register_middlewares
from sqlite_db import db
from admin_handlers import router as admin_router
from category_management import router as category_router
from product_management import router as product_router
from test_management import router as test_router
from user_management import router as user_router
from statistics import router as stats_router
from system_tests import run_system_tests

# Initialize bot with more detailed logging
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    session=ClientSession()  # Use aiohttp ClientSession for better logging
)

# Add callback answer middleware
dp.callback_query.middleware(CallbackAnswerMiddleware())

# Register handlers
async def register_handlers():
    """Register all message and callback handlers"""
    logger.info("Registering bot handlers")
    # Include routers
    dp.include_router(admin_router)
    dp.include_router(category_router)
    dp.include_router(product_router)
    dp.include_router(test_router)
    dp.include_router(user_router)
    dp.include_router(stats_router)
    
    # Register basic commands
    @dp.message(Command("start"))
    async def start_command(message: types.Message):
        """Handle /start command"""
        try:
            # Register user
            user_data = {
                'telegram_id': message.from_user.id,
                'first_name': message.from_user.first_name,
                'last_name': message.from_user.last_name,
                'username': message.from_user.username
            }
            db.register_user(user_data)
            
            # Send welcome message
            welcome_text = (
                "👋 Добро пожаловать в бот Морковка!\n\n"
                "Я помогу вам узнать больше о наших продуктах и пройти тестирование.\n\n"
                "Доступные команды:\n"
                "/help - Показать справку\n"
                "/search - Поиск продуктов\n"
                "/tests - Список тестов\n"
                "/profile - Ваш профиль"
            )
            
            if message.from_user.id in ADMIN_IDS:
                welcome_text += "\n\nАдминистративные команды:\n"
                welcome_text += "/admin - Панель администратора\n"
                welcome_text += "/stats - Статистика\n"
                welcome_text += "/export_stats - Экспорт статистики"
            
            await message.answer(welcome_text)
            logger.info(f"User {message.from_user.id} started the bot")
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

# Create application instance
app = web.Application()

# Add health check endpoint
async def health_check(request):
    """Health check endpoint"""
    logger.info("Health check requested")
    return web.Response(text="OK")

app.router.add_get("/health", health_check)

# Add root endpoint for Render health checks
async def root(request):
    """Root endpoint for Render health checks"""
    logger.info("Root endpoint requested")
    return web.Response(text="Bot server is running")

app.router.add_get("/", root)

# Add webhook handler
async def webhook_handler(request: web.Request) -> web.Response:
    """Handle incoming webhook requests"""
    try:
        update = types.Update.model_validate(await request.json())
        logger.debug(f"Received update: {update.model_dump_json()}")
        
        await dp.feed_update(bot, update)
        return web.Response()
        
    except Exception as e:
        logger.error(f"Webhook handler error: {e}", exc_info=True)
        return web.Response(status=500)

app.router.add_post(WEBHOOK_PATH, webhook_handler)

# Startup and shutdown handlers
async def on_startup(application: web.Application) -> None:
    """Initialize bot on startup"""
    try:
        logger.info("Starting bot initialization")
        
        # Initialize database
        if not db.check_database_integrity():
            logger.error("Database integrity check failed")
            raise RuntimeError("Database integrity check failed")
        
        # Register handlers
        await register_handlers()
        
        # Register middlewares
        register_middlewares(dp)
        
        # Set webhook in production
        if ENVIRONMENT == "production":
            if not WEBHOOK_URL:
                raise ValueError("WEBHOOK_URL is required in production mode")
            
            logger.info(f"Setting webhook to {WEBHOOK_URL}")
            
            try:
                await bot.set_webhook(url=WEBHOOK_URL)
                logger.info("Webhook set successfully")
            except Exception as e:
                logger.error(f"Failed to set webhook: {e}")
                raise
            
            # Create admin users if needed
            for admin_id in ADMIN_IDS:
                user = db.get_user(admin_id)
                if not user or not user.get('is_admin'):
                    db.register_user({
                        'telegram_id': admin_id,
                        'is_admin': 1
                    })
                    logger.info(f"Created admin user: {admin_id}")
        
        # Log bot info
        bot_info = await bot.get_me()
        logger.info(
            f"Bot started: @{bot_info.username} "
            f"(ID: {bot_info.id}, Name: {bot_info.full_name})"
        )
        
        # Cleanup old logs
        cleanup_old_logs()
        
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise

async def on_shutdown(application: web.Application) -> None:
    """Cleanup on shutdown"""
    try:
        # Remove webhook
        if WEBHOOK_HOST:
            logger.info("Removing webhook")
            await bot.delete_webhook()
        
        # Close database connection
        logger.info("Closing database connection")
        db.close()
        
        # Close bot session
        logger.info("Closing bot session")
        await bot.session.close()
        
    except Exception as e:
        logger.error(f"Shutdown failed: {e}", exc_info=True)
        raise

# Add startup and shutdown handlers
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

# Setup application for webhook
setup_application(app, dp, bot=bot)

def main() -> None:
    """Main function to run the bot"""
    try:
        logger.info(f"Starting web server on port {PORT}")
        
        # Run the application
        web.run_app(
            app,
            host=WEBAPP_HOST,
            port=PORT,  # Use the port we got at startup
            access_log=logger
        )
    except Exception as e:
        logger.error(f"Application failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    logger.info("Starting bot application")
    main()
