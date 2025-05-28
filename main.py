import logging
import os
import sys
import time
import asyncio
from typing import Optional

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

# Local imports
from config import (
    BOT_TOKEN,
    WEBHOOK_URL,
    WEBHOOK_PATH,
    ENVIRONMENT
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

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout,
    force=True  # Force reconfiguration of logging
)

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add file handler for persistent logging
if ENVIRONMENT == "production":
    log_file = "bot.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(file_handler)

# Initialize bot
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
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

# Register handlers
def register_handlers():
    """Register all handlers with the dispatcher"""
    # Command handlers
    dp.message.register(start_command, CommandStart())
    dp.message.register(start_command, Command("help"))
    dp.message.register(any_message)
    
    # Knowledge base handlers
    dp.callback_query.register(kb_callback, F.data == "knowledge_base")
    dp.callback_query.register(cat_callback, F.data.startswith("category:"))
    dp.callback_query.register(prod_callback, F.data.startswith("product:"))
    
    # Testing handlers
    dp.callback_query.register(testing_callback, F.data == "testing")
    dp.callback_query.register(test_select_callback, F.data.startswith("test_select:"))
    dp.callback_query.register(test_answer_callback, F.data.startswith("test_answer:"))
    dp.callback_query.register(test_result_callback, F.data.startswith("test_result:"))
    
    # Admin handlers
    dp.callback_query.register(admin_callback, F.data == "admin")
    dp.callback_query.register(admin_cat_callback, F.data.startswith("admin_categories"))
    dp.callback_query.register(admin_prod_callback, F.data.startswith("admin_products"))
    dp.callback_query.register(admin_test_callback, F.data.startswith("admin_tests"))
    dp.callback_query.register(admin_stats_callback, F.data.startswith("admin_stats"))
    
    # Search handlers
    dp.message.register(search_command, F.text == "🔍 Поиск")
    dp.message.register(search_query_command, F.text.startswith("🔍 "))
    
    # Logging callback queries
    dp.callback_query.register(log_callback_queries)

# Command handlers
async def start_command(message: types.Message):
    logger.info(f"Start command from user {message.from_user.id}")
    await start(message, None)

async def any_message(message: types.Message):
    logger.info(f"Message from user {message.from_user.id}: {message.text}")
    await register_user_handler(message, None)

# Callback handlers
async def kb_callback(callback_query: types.CallbackQuery):
    logger.info(f"Knowledge base callback from user {callback_query.from_user.id}")
    await knowledge_base_handler(callback_query, None)

async def cat_callback(callback_query: types.CallbackQuery):
    logger.info(f"Category callback from user {callback_query.from_user.id}: {callback_query.data}")
    await category_handler(callback_query, None)

async def prod_callback(callback_query: types.CallbackQuery):
    logger.info(f"Product callback from user {callback_query.from_user.id}: {callback_query.data}")
    await product_handler(callback_query, None)

async def testing_callback(callback_query: types.CallbackQuery):
    logger.info(f"Testing callback from user {callback_query.from_user.id}")
    await testing_handler(callback_query, None)

async def test_select_callback(callback_query: types.CallbackQuery):
    logger.info(f"Test selection callback from user {callback_query.from_user.id}: {callback_query.data}")
    await test_selection_handler(callback_query, None)

async def test_answer_callback(callback_query: types.CallbackQuery):
    logger.info(f"Test answer callback from user {callback_query.from_user.id}: {callback_query.data}")
    await test_question_handler(callback_query, None)

async def test_result_callback(callback_query: types.CallbackQuery):
    logger.info(f"Test result callback from user {callback_query.from_user.id}: {callback_query.data}")
    await test_result_handler(callback_query, None)

async def admin_callback(callback_query: types.CallbackQuery):
    logger.info(f"Admin callback from user {callback_query.from_user.id}")
    await admin_handler(callback_query, None)

async def admin_cat_callback(callback_query: types.CallbackQuery):
    logger.info(f"Admin category callback from user {callback_query.from_user.id}: {callback_query.data}")
    await admin_categories_handler(callback_query, None)

async def admin_prod_callback(callback_query: types.CallbackQuery):
    logger.info(f"Admin product callback from user {callback_query.from_user.id}: {callback_query.data}")
    await admin_products_handler(callback_query, None)

async def admin_test_callback(callback_query: types.CallbackQuery):
    logger.info(f"Admin test callback from user {callback_query.from_user.id}: {callback_query.data}")
    await admin_tests_handler(callback_query, None)

async def admin_stats_callback(callback_query: types.CallbackQuery):
    logger.info(f"Admin stats callback from user {callback_query.from_user.id}: {callback_query.data}")
    await admin_stats_handler(callback_query, None)

async def search_command(message: types.Message):
    logger.info(f"Search command from user {message.from_user.id}")
    await search_handler(message, None)

async def search_query_command(message: types.Message):
    logger.info(f"Search query from user {message.from_user.id}: {message.text}")
    await search_handler(message, None)

async def log_callback_queries(callback: types.CallbackQuery):
    logger.info(f"Callback query from user {callback.from_user.id}: {callback.data}")
    await callback.answer()

# Startup and shutdown handlers
async def on_startup(bot: Bot) -> None:
    """Actions on bot startup"""
    logger.info("Starting bot...")
    if ENVIRONMENT == "production":
        try:
            # Remove existing webhook
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Removed existing webhook")
            
            # Set new webhook
            await bot.set_webhook(
                url=WEBHOOK_URL,
                allowed_updates=["message", "callback_query", "inline_query"],
                drop_pending_updates=True
            )
            logger.info(f"Webhook set to {WEBHOOK_URL}")
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}", exc_info=True)
            raise
    else:
        logger.info("Running in development mode (polling)")

async def on_shutdown(bot: Bot) -> None:
    """Actions on bot shutdown"""
    logger.info("Shutting down bot...")
    if ENVIRONMENT == "production":
        await bot.delete_webhook()
        logger.info("Webhook removed")
    await bot.session.close()

# Main application setup
async def main() -> None:
    """Main function to run the bot"""
    try:
        # Register all handlers
        register_handlers()
        
        # Set up startup and shutdown handlers
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        
        if ENVIRONMENT == "production":
            # Webhook mode
            app = web.Application()
            
            # Health check endpoint
            async def health_check(request: web.Request) -> web.Response:
                return web.Response(text="OK")
            
            app.router.add_get("/health", health_check)
            
            # Webhook handler
            webhook_handler = SimpleRequestHandler(
                dispatcher=dp,
                bot=bot,
                webhook_path=WEBHOOK_PATH
            )
            webhook_handler.register(app, path=WEBHOOK_PATH)
            
            # Set up application
            setup_application(app, dp, bot=bot)
            
            # Run webhook
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8000)))
            await site.start()
            
            logger.info("Bot started in webhook mode")
            
            # Keep the application running
            while True:
                await asyncio.sleep(3600)
        else:
            # Polling mode
            logger.info("Starting bot in polling mode...")
            await dp.start_polling(bot)
            
    except Exception as e:
        logger.error(f"Critical error in main: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Bot stopped due to error: {e}", exc_info=True)
        sys.exit(1)

@dp.errors()
async def errors_handler(update: types.Update, exception: Exception):
    logger.error(f"Update {update} caused error: {exception}")
    return True  # Подавляем ошибку

@dp.middleware()
async def timing_middleware(handler, event, data):
    start = time.time()
    try:
        return await handler(event, data)
    finally:
        logging.info(f"Handler {handler.__name__} executed in {time.time()-start:.3f}s")
