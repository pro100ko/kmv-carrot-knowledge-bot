import logging
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
# Изменяем импорт фильтра Text
from aiogram.filters import Text
from aiogram.utils.webhook import configure_app, SimpleRequestHandler
import asyncio
from aiohttp import web

# Импортируем настройки
from config import BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PATH

# Импортируем обработчики
from handlers.user_management import register_user_handler, start
from handlers.knowledge_base import knowledge_base_handler, category_handler, product_handler, search_handler
from handlers.testing import testing_handler, test_selection_handler, test_question_handler, test_result_handler
from handlers.admin import admin_handler, admin_categories_handler, admin_products_handler, admin_tests_handler, admin_stats_handler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Регистрируем обработчики
@dp.message(CommandStart())
@dp.message(Command("help"))
async def start_command(message: types.Message):
    await start(message, None)

# Колбэки для базы знаний
@dp.callback_query(Text(text="knowledge_base"))
async def kb_callback(callback_query: types.CallbackQuery):
    await knowledge_base_handler(callback_query, None)

@dp.callback_query(lambda c: c.data.startswith("category:"))
async def cat_callback(callback_query: types.CallbackQuery):
    await category_handler(callback_query, None)

@dp.callback_query(lambda c: c.data.startswith("product:"))
async def prod_callback(callback_query: types.CallbackQuery):
    await product_handler(callback_query, None)

# Колбэки для тестирования
@dp.callback_query(Text(text="testing"))
async def testing_callback(callback_query: types.CallbackQuery):
    await testing_handler(callback_query, None)

@dp.callback_query(lambda c: c.data.startswith("test_select:"))
async def test_select_callback(callback_query: types.CallbackQuery):
    await test_selection_handler(callback_query, None)

@dp.callback_query(lambda c: c.data.startswith("test_answer:"))
async def test_answer_callback(callback_query: types.CallbackQuery):
    await test_question_handler(callback_query, None)

@dp.callback_query(lambda c: c.data.startswith("test_result:"))
async def test_result_callback(callback_query: types.CallbackQuery):
    await test_result_handler(callback_query, None)

# Колбэки для админки
@dp.callback_query(Text(text="admin"))
async def admin_callback(callback_query: types.CallbackQuery):
    await admin_handler(callback_query, None)

@dp.callback_query(lambda c: c.data.startswith("admin_categories"))
async def admin_cat_callback(callback_query: types.CallbackQuery):
    await admin_categories_handler(callback_query, None)

@dp.callback_query(lambda c: c.data.startswith("admin_products"))
async def admin_prod_callback(callback_query: types.CallbackQuery):
    await admin_products_handler(callback_query, None)

@dp.callback_query(lambda c: c.data.startswith("admin_tests"))
async def admin_test_callback(callback_query: types.CallbackQuery):
    await admin_tests_handler(callback_query, None)

@dp.callback_query(lambda c: c.data.startswith("admin_stats"))
async def admin_stats_callback(callback_query: types.CallbackQuery):
    await admin_stats_handler(callback_query, None)

# Обработчики для текстовых сообщений
@dp.message(lambda message: message.text == "🔍 Поиск")
async def search_command(message: types.Message):
    await search_handler(message, None)

@dp.message(lambda message: message.text and message.text.startswith("🔍 "))
async def search_query_command(message: types.Message):
    await search_handler(message, None)

# Обработчик для прочих сообщений
@dp.message()
async def any_message(message: types.Message):
    await register_user_handler(message, None)

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

async def main() -> None:
    """Запуск бота"""
    if os.environ.get("ENVIRONMENT") == "production":
        # В режиме production используем webhook
        # Создаем приложение aiohttp
        app = web.Application()
        
        # Настраиваем вебхук
        SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        ).register(app, path=WEBHOOK_PATH)
        
        # Дополнительные обработчики маршрутов
        app.on_startup.append(lambda app: on_startup(bot))
        app.on_shutdown.append(lambda app: on_shutdown(bot))
        
        # Запускаем веб-приложение
        port = int(os.environ.get("PORT", 8443))
        logger.info(f"Запуск webhook на порту {port}")
        web.run_app(app, host="0.0.0.0", port=port)
    else:
        # В режиме разработки используем polling
        await dp.start_polling(bot, on_startup=on_startup, on_shutdown=on_shutdown)
        logger.info("Бот запущен в режиме polling")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
