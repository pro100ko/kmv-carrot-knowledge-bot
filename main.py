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
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

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

# Command handlers
@dp.message(CommandStart())
@dp.message(Command("help"))
async def start_command(message: types.Message):
    await start(message, None)

@dp.message()
async def any_message(message: types.Message):
    await register_user_handler(message, None)

# Callback handlers for knowledge base
@dp.callback_query(F.data == "knowledge_base")
async def kb_callback(callback_query: types.CallbackQuery):
    await knowledge_base_handler(callback_query, None)

@dp.callback_query(F.data.startswith("category:"))
async def cat_callback(callback_query: types.CallbackQuery):
    await category_handler(callback_query, None)

@dp.callback_query(F.data.startswith("product:"))
async def prod_callback(callback_query: types.CallbackQuery):
    await product_handler(callback_query, None)

# Callback handlers for testing
@dp.callback_query(F.data == "testing")
async def testing_callback(callback_query: types.CallbackQuery):
    await testing_handler(callback_query, None)

@dp.callback_query(F.data.startswith("test_select:"))
async def test_select_callback(callback_query: types.CallbackQuery):
    await test_selection_handler(callback_query, None)

@dp.callback_query(F.data.startswith("test_answer:"))
async def test_answer_callback(callback_query: types.CallbackQuery):
    await test_question_handler(callback_query, None)

@dp.callback_query(F.data.startswith("test_result:"))
async def test_result_callback(callback_query: types.CallbackQuery):
    await test_result_handler(callback_query, None)

# Callback handlers for admin panel
@dp.callback_query(F.data == "admin")
async def admin_callback(callback_query: types.CallbackQuery):
    await admin_handler(callback_query, None)

@dp.callback_query(F.data.startswith("admin_categories"))
async def admin_cat_callback(callback_query: types.CallbackQuery):
    await admin_categories_handler(callback_query, None)

@dp.callback_query(F.data.startswith("admin_products"))
async def admin_prod_callback(callback_query: types.CallbackQuery):
    await admin_products_handler(callback_query, None)

@dp.callback_query(F.data.startswith("admin_tests"))
async def admin_test_callback(callback_query: types.CallbackQuery):
    await admin_tests_handler(callback_query, None)

@dp.callback_query(F.data.startswith("admin_stats"))
async def admin_stats_callback(callback_query: types.CallbackQuery):
    await admin_stats_handler(callback_query, None)

# Search handlers
@dp.message(F.text == "🔍 Поиск")
async def search_command(message: types.Message):
    await search_handler(message, None)

@dp.message(F.text.startswith("🔍 "))
async def search_query_command(message: types.Message):
    await search_handler(message, None)

# Logging callback queries
@dp.callback_query()
async def log_callback_queries(callback: types.CallbackQuery):
    logger.info(f"Received callback: {callback.data}")
    await callback.answer()

# Startup and shutdown handlers
async def on_startup(bot: Bot) -> None:
    """Actions on bot startup"""
    if ENVIRONMENT == "production":
        try:
            await bot.set_webhook(
                url=WEBHOOK_URL,
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True
            )
            logger.info(f"Webhook set to {WEBHOOK_URL}")
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
            raise

async def on_shutdown(bot: Bot) -> None:
    """Actions on bot shutdown"""
    if ENVIRONMENT == "production":
        await bot.delete_webhook()
        logger.info("Webhook removed")

# Error handlers
async def on_telegram_error(update: Optional[types.Update], exception: Exception) -> bool:
    if isinstance(exception, TelegramBadRequest) and "message is not modified" in str(exception):
        return True
    logger.error(f"Telegram error: {exception}")
    return True

dp.errors.register(on_telegram_error)

@dp.update()
async def unhandled_update_handler(update: types.Update):
    logger.warning(f"Unhandled update: {update}")
    if update.message:
        await update.message.answer("Извините, я не понял эту команду")

# Main application
async def main() -> None:
    """Start the bot"""
    if ENVIRONMENT == "production":
        # Production mode with webhook
        app = web.Application()
        
        # Health check endpoint
        async def health_check(request: web.Request) -> web.Response:
            return web.Response(text="OK", status=200)
        
        app.router.add_get("/health", health_check)
        
        # Setup webhook handler
        webhook_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        )
        webhook_handler.register(app, path=WEBHOOK_PATH)
        
        # Setup application with dispatcher
        setup_application(app, dp, bot=bot)
        
        # Register startup and shutdown callbacks
        app.on_startup.append(lambda app: asyncio.create_task(on_startup(bot)))
        app.on_shutdown.append(lambda app: asyncio.create_task(on_shutdown(bot)))
        
        # Start web application
        port = int(os.environ.get("PORT", 8443))
        logger.info(f"Starting webhook on port {port}")
        
        return await web._run_app(app, host="0.0.0.0", port=port)
    else:
        # Development mode with long polling
        logger.info("Starting bot in development mode (long polling)")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Critical error: {e}")
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
