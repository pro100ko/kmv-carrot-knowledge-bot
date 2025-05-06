
import logging
import os
import sys
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode

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

def main() -> None:
    """Запуск бота"""
    # Создаем объект приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики
    # Обработчики для команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    
    # Регистрируем обработчики кнопок
    application.add_handler(CallbackQueryHandler(knowledge_base_handler, pattern="^knowledge_base$"))
    application.add_handler(CallbackQueryHandler(category_handler, pattern="^category:"))
    application.add_handler(CallbackQueryHandler(product_handler, pattern="^product:"))
    
    application.add_handler(CallbackQueryHandler(testing_handler, pattern="^testing$"))
    application.add_handler(CallbackQueryHandler(test_selection_handler, pattern="^test_select:"))
    application.add_handler(CallbackQueryHandler(test_question_handler, pattern="^test_answer:"))
    application.add_handler(CallbackQueryHandler(test_result_handler, pattern="^test_result:"))
    
    application.add_handler(CallbackQueryHandler(admin_handler, pattern="^admin$"))
    application.add_handler(CallbackQueryHandler(admin_categories_handler, pattern="^admin_categories"))
    application.add_handler(CallbackQueryHandler(admin_products_handler, pattern="^admin_products"))
    application.add_handler(CallbackQueryHandler(admin_tests_handler, pattern="^admin_tests"))
    application.add_handler(CallbackQueryHandler(admin_stats_handler, pattern="^admin_stats"))
    
    # Обработчик для поиска
    application.add_handler(MessageHandler(filters.Regex(r'^\🔍 Поиск$'), search_handler))
    application.add_handler(MessageHandler(filters.Regex(r'^\🔍 .*'), search_handler))
    
    # Обработчик для всех остальных сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, register_user_handler))
    
    # Запускаем бота
    if os.environ.get("ENVIRONMENT") == "production":
        # На продакшн-сервере используем webhook
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8443)),
            url_path=WEBHOOK_PATH,
            webhook_url=WEBHOOK_URL
        )
        logger.info(f"Webhook установлен на {WEBHOOK_URL}")
    else:
        # Локально используем polling
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Бот запущен в режиме polling")
    
if __name__ == '__main__':
    main()
