import logging
import os
import sys
import time
import asyncio
from typing import Optional, Callable, Dict, Any

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
    WEBAPP_PORT,
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

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', mode='a', encoding='utf-8')
    ],
    force=True  # Force reconfiguration of logging
)

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add file handler for persistent logging
if ENVIRONMENT == "production":
    log_file = "bot.log"
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(file_handler)

# Initialize bot with more detailed logging
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    session=ClientSession()  # Use aiohttp ClientSession for better logging
)

# Initialize SQLite
sqlite_initialized = False
try:
    import sqlite_db
    if sqlite_db.SQLITE_AVAILABLE:
        sqlite_initialized = True
        logger.info("SQLite successfully initialized and working")
    else:
        logger.error("Failed to initialize SQLite. Bot cannot work without database")
        sys.exit(1)
except Exception as e:
    logger.error(f"Critical error during SQLite initialization: {e}")
    logger.error("Bot cannot work without database")
    sys.exit(1)

# Add callback answer middleware
dp.callback_query.middleware(CallbackAnswerMiddleware())

# Register handlers
async def register_handlers():
    """Register all message and callback handlers"""
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
    
    @dp.message(Command("help"))
    async def help_command(message: types.Message):
        """Handle /help command"""
        try:
            help_text = (
                "📚 Справка по командам бота:\n\n"
                "Основные команды:\n"
                "/start - Начать работу с ботом\n"
                "/help - Показать эту справку\n"
                "/search - Поиск продуктов\n"
                "/tests - Список доступных тестов\n"
                "/profile - Ваш профиль и статистика\n\n"
                "Поиск продуктов:\n"
                "• Используйте /search для поиска продуктов\n"
                "• Введите название или описание продукта\n"
                "• Минимальная длина запроса: 3 символа\n\n"
                "Тестирование:\n"
                "• Используйте /tests для просмотра доступных тестов\n"
                "• Выберите тест для начала\n"
                "• Отвечайте на вопросы в течение отведенного времени\n"
                "• Получите результаты и объяснения после завершения"
            )
            
            if message.from_user.id in ADMIN_IDS:
                help_text += "\n\nАдминистративные команды:\n"
                help_text += "/admin - Панель администратора\n"
                help_text += "/stats - Просмотр статистики\n"
                help_text += "/export_stats - Экспорт статистики в Excel\n"
                help_text += "/system_test - Запуск системных тестов"
            
            await message.answer(help_text)
            logger.info(f"User {message.from_user.id} requested help")
            
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")
    
    @dp.message(Command("system_test"))
    async def system_test_command(message: types.Message):
        """Handle /system_test command"""
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("⛔ У вас нет доступа к этой команде.")
            return
        
        try:
            # Send initial message
            status_message = await message.answer("🔄 Запуск системных тестов...")
            
            # Run tests
            await run_system_tests()
            
            # Update status message
            await status_message.edit_text("✅ Системные тесты успешно завершены!")
            logger.info(f"Admin {message.from_user.id} ran system tests")
            
        except Exception as e:
            logger.error(f"Error in system test command: {e}")
            await message.answer("❌ Ошибка при выполнении системных тестов.")
    
    @dp.message()
    async def any_message(message: types.Message):
        """Handle any other message"""
        try:
            # Register user activity
            db.register_user({
                'telegram_id': message.from_user.id,
                'first_name': message.from_user.first_name,
                'last_name': message.from_user.last_name,
                'username': message.from_user.username
            })
            
            # Log message
            logger.info(
                f"User {message.from_user.id} sent message: {message.text[:100]}"
                + ("..." if len(message.text) > 100 else "")
            )
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")

# Startup and shutdown handlers
async def on_startup(application: web.Application) -> None:
    """Initialize bot on startup"""
    try:
        # Log port information
        app_logger.info(f"Starting application on port {WEBAPP_PORT}")
        
        # Initialize database
        if not db.check_database_integrity():
            app_logger.error("Database integrity check failed")
            raise RuntimeError("Database integrity check failed")
        
        # Register handlers
        await register_handlers()
        
        # Register middlewares
        register_middlewares(dp)
        
        # Set webhook in production
        if ENVIRONMENT == "production":
            if not WEBHOOK_URL:
                raise ValueError("WEBHOOK_URL is required in production mode")
            
            webhook_logger.info(f"Setting webhook to {WEBHOOK_URL}")
            
            try:
                # In production, we don't need to provide a certificate as Render handles SSL
                await bot.set_webhook(url=WEBHOOK_URL)
                webhook_logger.info("Webhook set successfully")
            except Exception as e:
                webhook_logger.error(f"Failed to set webhook: {e}")
                raise
            
            # Create admin users if needed
            for admin_id in ADMIN_IDS:
                user = db.get_user(admin_id)
                if not user or not user.get('is_admin'):
                    db.register_user({
                        'telegram_id': admin_id,
                        'is_admin': 1
                    })
                    app_logger.info(f"Created admin user: {admin_id}")
        
        # Log bot info
        bot_info = await bot.get_me()
        app_logger.info(
            f"Bot started: @{bot_info.username} "
            f"(ID: {bot_info.id}, Name: {bot_info.full_name})"
        )
        
        # Cleanup old logs
        cleanup_old_logs()
        
    except Exception as e:
        app_logger.error(f"Startup failed: {e}", exc_info=True)
        raise

async def on_shutdown(application: web.Application) -> None:
    """Cleanup on shutdown"""
    try:
        # Remove webhook
        if WEBHOOK_HOST:
            webhook_logger.info("Removing webhook")
            await bot.delete_webhook()
        
        # Close database connection
        app_logger.info("Closing database connection")
        db.close()
        
        # Close bot session
        app_logger.info("Closing bot session")
        await bot.session.close()
        
    except Exception as e:
        app_logger.error(f"Shutdown failed: {e}", exc_info=True)
        raise

async def webhook_handler(request: web.Request) -> web.Response:
    """Handle incoming webhook requests"""
    try:
        update = types.Update.model_validate(await request.json())
        webhook_logger.debug(f"Received update: {update.model_dump_json()}")
        
        await dp.feed_update(bot, update)
        return web.Response()
        
    except Exception as e:
        webhook_logger.error(f"Webhook handler error: {e}", exc_info=True)
        return web.Response(status=500)

# Create application instance
app = web.Application()

# Add startup and shutdown handlers
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

# Add webhook handler
app.router.add_post(WEBHOOK_PATH, webhook_handler)

# Add health check endpoint
async def health_check(request):
    return web.Response(text="OK")
app.router.add_get("/health", health_check)

# Set port for web server
if ENVIRONMENT == "production":
    WEBAPP_PORT = 8443
else:
    WEBAPP_PORT = int(os.getenv("PORT", os.getenv("WEBAPP_PORT", "8000")))

def main() -> None:
    """Main function to run the bot"""
    try:
        if ENVIRONMENT == "production":
            # Production mode with webhook
            webhook_logger.info(f"Starting in production mode with webhook on port {WEBAPP_PORT}")
            setup_application(app, dp, bot=bot)
            print(f"Starting web server on {WEBAPP_HOST}:{WEBAPP_PORT}")
            web.run_app(
                app,
                host=WEBAPP_HOST,
                port=WEBAPP_PORT,
                access_log=webhook_logger
            )
        else:
            # Development mode with polling
            app_logger.info("Starting in development mode with polling")
            async def start_polling():
                await dp.start_polling(bot)
            asyncio.run(start_polling())
    except Exception as e:
        app_logger.error(f"Application failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()

# Export the app instance for Gunicorn
__all__ = ['app']

@dp.middleware()
async def timing_middleware(handler: Callable, event: types.Update, data: Dict[str, Any]):
    start = time.time()
    try:
        return await handler(event, data)
    finally:
        logging.info(f"Handler {handler.__name__} executed in {time.time()-start:.3f}s")
