
import logging
import os
import sys
import json
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters.command import Command, CommandStart
# В aiogram 3.20.0 используем magic_filter модуль для фильтрации
from magic_filter import F
# Используем правильные импорты для вебхука в aiogram 3.x
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
import asyncio
from aiohttp import web
import firebase_admin
from firebase_admin import credentials

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
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()  # Создаем экземпляр диспетчера

# Инициализация Firebase
try:
    # Вариант 1: Через файл учетных данных
    if os.path.exists("morkovka-kmv-bot-31365aded116.json"):
        cred = credentials.Certificate("morkovka-kmv-bot-31365aded116.json")
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
            logger.info("Firebase инициализирован через файл учетных данных")
    # Вариант 2: Через переменную окружения
    elif os.environ.get('FIREBASE_CONFIG'):
        try:
            cred_dict = json.loads(os.environ.get('FIREBASE_CONFIG'))
            cred = credentials.Certificate(cred_dict)
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
                logger.info("Firebase инициализирован через переменную окружения")
        except Exception as e:
            logger.error(f"Ошибка инициализации Firebase из переменной окружения: {e}")
    else:
        logger.warning("Не найдены учетные данные Firebase")
except Exception as e:
    logger.error(f"Ошибка при инициализации Firebase: {e}")

# Регистрируем обработчики
@dp.message(CommandStart())
@dp.message(Command("help"))
async def start_command(message: types.Message):
    await start(message, None)

# Колбэки для базы знаний
@dp.callback_query(F.data == "knowledge_base")
async def kb_callback(callback_query: types.CallbackQuery):
    await knowledge_base_handler(callback_query, None)

@dp.callback_query(F.data.startswith("category:"))
async def cat_callback(callback_query: types.CallbackQuery):
    await category_handler(callback_query, None)

@dp.callback_query(F.data.startswith("product:"))
async def prod_callback(callback_query: types.CallbackQuery):
    await product_handler(callback_query, None)

# Колбэки для тестирования
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

# Колбэки для админки
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

# Обработчики для текстовых сообщений
@dp.message(F.text == "🔍 Поиск")
async def search_command(message: types.Message):
    await search_handler(message, None)

@dp.message(F.text.startswith("🔍 "))
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
        
        # Настраиваем вебхук (используем новый API aiogram 3.x)
        webhook_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        )
        webhook_handler.register(app, path=WEBHOOK_PATH)
        
        # Настраиваем приложение с диспетчером
        setup_application(app, dp, bot=bot)
        
        # Регистрируем колбеки для запуска и остановки
        async def on_startup_app(app):
            await on_startup(bot)
            
        async def on_shutdown_app(app):
            await on_shutdown(bot)
            
        app.on_startup.append(on_startup_app)
        app.on_shutdown.append(on_shutdown_app)
        
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
