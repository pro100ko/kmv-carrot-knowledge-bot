import logging
import os
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.client.default import DefaultBotProperties
from aiogram.filters.command import Command, CommandStart
import asyncio
from aiohttp import web
from aiogram import Bot
from dispatcher import dp  # Импортируем dp
from .handlers import admin, knowledge_base, testing  # Импортируем обработчики после инициализации dp

# Импортируем настройки
from config import BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PATH

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

from handlers.admin import (
    admin_handler,
    admin_categories_handler,
    admin_products_handler,
    create_category_handler,
    create_product_handler
)

# Инициализация SQLite
sqlite_initialized = False
try:
    import sqlite_db
    if sqlite_db.SQLITE_AVAILABLE:
        sqlite_initialized = True
        logger.info("SQLite успешно проинициализирована и работает")
    else:
        logger.error("SQLite не удалось инициализировать. Бот не может работать без базы данных")
        sys.exit(1)
except Exception as e:
    logger.error(f"Критическая ошибка при инициализации SQLite: {e}")
    logger.error("Бот не может работать без базы данных")
    sys.exit(1)

# Обработчик команды /start и /help
@dp.message(CommandStart())
@dp.message(Command("help"))
async def start_command(message: types.Message):
    from handlers.user_management import start
    await start(message, None)

# Обработчик для прочих сообщений
@dp.message()
async def any_message(message: types.Message):
    from handlers.user_management import register_user_handler
    await register_user_handler(message, None)

# Колбэки для базы знаний
@dp.callback_query(F.data == "knowledge_base")
async def kb_callback(callback_query: types.CallbackQuery):
    from handlers.knowledge_base import knowledge_base_handler
    await knowledge_base_handler(callback_query, None)

@dp.callback_query(F.data.startswith("category:"))
async def cat_callback(callback_query: types.CallbackQuery):
    from handlers.knowledge_base import category_handler
    await category_handler(callback_query, None)

@dp.callback_query(F.data.startswith("product:"))
async def prod_callback(callback_query: types.CallbackQuery):
    from handlers.knowledge_base import product_handler
    await product_handler(callback_query, None)

# Колбэки для тестирования
@dp.callback_query(F.data == "testing")
async def testing_callback(callback_query: types.CallbackQuery):
    from handlers.testing import testing_handler
    await testing_handler(callback_query, None)

@dp.callback_query(F.data.startswith("test_select:"))
async def test_select_callback(callback_query: types.CallbackQuery):
    from handlers.testing import test_selection_handler
    await test_selection_handler(callback_query, None)

@dp.callback_query(F.data.startswith("test_answer:"))
async def test_answer_callback(callback_query: types.CallbackQuery):
    from handlers.testing import test_question_handler
    await test_question_handler(callback_query, None)

@dp.callback_query(F.data.startswith("test_result:"))
async def test_result_callback(callback_query: types.CallbackQuery):
    from handlers.testing import test_result_handler
    await test_result_handler(callback_query, None)

# Колбэки для админки
@dp.callback_query(F.data == "admin")
async def admin_callback(callback_query: types.CallbackQuery):
    from handlers.admin import admin_handler
    await admin_handler(callback_query, None)

@dp.callback_query(F.data.startswith("admin_categories"))
async def admin_cat_callback(callback_query: types.CallbackQuery):
    from handlers.admin import admin_categories_handler
    await admin_categories_handler(callback_query, None)

@dp.callback_query(F.data.startswith("admin_products"))
async def admin_prod_callback(callback_query: types.CallbackQuery):
    from handlers.admin import admin_products_handler
    await admin_products_handler(callback_query, None)

@dp.callback_query(F.data.startswith("admin_tests"))
async def admin_test_callback(callback_query: types.CallbackQuery):
    from handlers.admin import admin_tests_handler
    await admin_tests_handler(callback_query, None)

@dp.callback_query(F.data.startswith("admin_stats"))
async def admin_stats_callback(callback_query: types.CallbackQuery):
    from handlers.admin import admin_stats_handler
    await admin_stats_handler(callback_query, None)

@dp.callback_query()
async def log_callback_queries(callback: types.CallbackQuery):
    logger.info(f"Received callback: {callback.data}")
    await callback.answer()  # Важно для предотвращения "часиков" в интерфейсе

# Обработчики для текстовых сообщений
@dp.message(F.text == "🔍 Поиск")
async def search_command(message: types.Message):
    from handlers.knowledge_base import search_handler
    await search_handler(message, None)

@dp.message(F.text.startswith("🔍 "))
async def search_query_command(message: types.Message):
    from handlers.knowledge_base import search_handler
    await search_handler(message, None)

async def on_startup(bot: Bot) -> None:
    """Действия при запуске бота"""
    # Устанавливаем вебхук
    await bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"Webhook установлен на {WEBHOOK_URL}")

async def on_shutdown(bot: Bot) -> None:
    """Действия при выключении бота"""
    # Удаляем вебхук
    await bot.delete_webhook()
    logger.info("Webhook удалён")

async def on_telegram_error(update, exception):
    if isinstance(exception, TelegramBadRequest) and "message is not modified" in str(exception):
        return True  # Игнорируем ошибку
    raise exception

dp.errors.register(on_telegram_error)

@dp.update()
async def unhandled_update_handler(update: types.Update):
    logger.warning(f"Unhandled update: {update}")
    # Можно добавить отправку сообщения пользователю
    if update.message:
        await update.message.answer("Извините, я не понял эту команду")

async def main() -> None:
    """Запуск бота"""
    if os.environ.get("ENVIRONMENT") == "production":
        # В режиме production используем webhook
        # Создаем приложение aiohttp
        await bot.set_webhook(WEBHOOK_URL)
        app = web.Application()
        
        # Настраиваем вебхук (используем новый API aiogram 3.x)
        from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
        
        webhook_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        )
        webhook_handler.register(app, path=WEBHOOK_PATH)
        
        # Настраиваем приложение с диспетчером
        setup_application(app, dp, bot=bot)
        
        # Регистрируем колбеки для запуска и остановки
        app.on_startup.append(lambda app: asyncio.create_task(on_startup(bot)))
        app.on_shutdown.append(lambda app: asyncio.create_task(on_shutdown(bot)))
        
        # Запускаем веб-приложение
        port = int(os.environ.get("PORT", 8443))
        logger.info(f"Запуск webhook на порту {port}")
        
        # Используем await для правильного запуска web-приложения
        return await web._run_app(app, host="0.0.0.0", port=port)
    else:
        await bot.delete_webhook()
        await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")

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
