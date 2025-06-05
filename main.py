"""Main application module."""

import asyncio
import logging
import signal
import sys
import os
from dotenv import load_dotenv
from typing import Optional, Callable, Any, Awaitable, Dict
from functools import wraps
import ssl
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

import config
# from config import (
#     BOT_TOKEN,
#     WEBHOOK_PATH,
#     WEBAPP_PORT,
#     WEBHOOK_SSL_CERT,
#     WEBHOOK_SSL_PRIV,
#     ENABLE_WEBHOOK,
#     ENABLE_METRICS,
#     LOG_LEVEL,
#     WEBHOOK_URL,
#     ENVIRONMENT,
#     IS_PRODUCTION,
#     WEBAPP_HOST
# )
from utils.db_pool import DatabasePool
from utils.resource_manager import ResourceManager
from logging_config import setup_logging
from middleware import (
    MetricsMiddleware,
    ErrorHandlingMiddleware,
    StateManagementMiddleware,
    LoggingMiddleware,
    AdminAccessMiddleware,
    UserActivityMiddleware,
    RateLimitMiddleware
)
from states import setup_states
from utils.webhook import setup_webhook
from utils.polling import setup_polling
from utils.health_check import create_health_check_handler
from monitoring.metrics import MetricsCollector
from utils.error_handling import handle_errors, log_operation
from utils.resource_manager import resource_manager
import sqlite_db

# Import handler setup functions
from handlers.user import setup_user_handlers
from handlers.catalog import setup_catalog_handlers
from handlers.tests import setup_test_handlers
from handlers.admin import setup_admin_handlers

# Configure logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info(f"Environment: {config.ENVIRONMENT}, IS_PRODUCTION: {config.IS_PRODUCTION}")

# Initialize bot and dispatcher
bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Create web application
app = web.Application()

# Store webhook handler for cleanup
webhook_handler: Optional[SimpleRequestHandler] = None

load_dotenv() # Load environment variables from .env file

async def setup_webhook(bot: Bot, dp: Dispatcher, webhook_url: str, webhook_path: str) -> None:
    """Configure webhook for the bot."""
    if not webhook_url:
        logger.error("WEBHOOK_URL is not set. Cannot configure webhook.")
        return

    try:
        # Remove any existing webhook
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Deleted existing webhook")

        # Set new webhook
        await bot.set_webhook(
            url=webhook_url,
            certificate=types.FSInputFile(config.WEBHOOK_SSL_CERT) if config.WEBHOOK_SSL_CERT else None,
            drop_pending_updates=True
        )
        logger.info(f"Webhook set to {webhook_url}")

        # Verify webhook
        webhook_info = await bot.get_webhook_info()
        logger.info(f"Webhook info: {webhook_info}")

        # Create and store webhook handler
        global webhook_handler
        webhook_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            handle_signals=False
        )
        
        # Register webhook handler with the app
        webhook_handler.register(app, path=webhook_path)
        setup_application(app, dp, bot=bot)
        logger.info(f"Webhook handler registered at path: {webhook_path}")
        
    except Exception as e:
        logger.error(f"Error setting up webhook: {e}", exc_info=True)
        raise

async def on_startup(runner_instance: Any) -> None:
    """Initialize application resources and start services."""
    logger.info("Entering on_startup function.")
    try:
        logger.info("Starting up application...")
        
        # Initialize database pool
        new_db_pool = DatabasePool(
            db_path=config.DB_PATH,
            max_connections=config.DB_MAX_CONNECTIONS,
            timeout=config.DB_TIMEOUT
        )
        await new_db_pool.initialize()  # Initialize the pool first
        
        # Store db_pool in both runner and dispatcher
        runner_instance['db_pool'] = new_db_pool
        dp.data['db_pool'] = new_db_pool
        
        # Initialize sqlite_db with the new pool
        sqlite_db.initialize(new_db_pool)
        await sqlite_db.db.initialize()  # Initialize the database instance
        
        # Initialize metrics collector
        metrics = MetricsCollector()  # Create new instance
        metrics.start()  # Start metrics collection
        runner_instance['metrics_collector'] = metrics
        dp.data['metrics_collector'] = metrics
        
        # Create and store health check handler
        health_check_handler = create_health_check_handler(metrics)  # Use the new instance
        runner_instance['health_check_handler'] = health_check_handler
        app.router.add_get('/health', health_check_handler)
        
        # Register middleware
        dp.update.middleware(MetricsMiddleware())
        dp.update.middleware(ErrorHandlingMiddleware())
        dp.update.middleware(StateManagementMiddleware())
        dp.update.middleware(LoggingMiddleware())
        dp.update.middleware(AdminAccessMiddleware())
        dp.update.middleware(UserActivityMiddleware())
        dp.update.middleware(RateLimitMiddleware())
        logger.info("Middleware registered")
        
        # Setup webhook or polling based on environment
        if config.IS_PRODUCTION:
            await setup_webhook(bot, dp, config.WEBHOOK_URL, config.WEBHOOK_PATH)
        else:
            await setup_polling(dp)
        
        # Setup bot commands
        await setup_bot_commands(bot)
        
        # Setup handlers
        setup_user_handlers(dp)
        setup_catalog_handlers(dp)
        setup_test_handlers(dp)
        setup_admin_handlers(dp)
        
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
        raise

async def on_shutdown(runner_instance: Any) -> None:
    """Clean up application resources."""
    logger.info("Entering on_shutdown function.")
    try:
        logger.info("Shutting down application...")
        
        # Stop metrics collection
        metrics_collector = runner_instance.get('metrics_collector')
        if metrics_collector:
            await metrics_collector.cleanup()  # Use cleanup instead of stop to ensure proper cleanup
            logger.info("Metrics collection stopped")
        
        # Stop webhook if running
        global webhook_handler
        if webhook_handler:
            await webhook_handler.shutdown()
            logger.info("Webhook server stopped")
        
        # Close database pool
        db_pool_instance = runner_instance.get('db_pool')
        if db_pool_instance:
            await db_pool_instance.close()
            logger.info("Database pool closed")
        
        # Close bot session
        await bot.session.close()
        logger.info("Bot session closed")
        
        logger.info("Application shutdown completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)
        raise

def handle_exception(loop: asyncio.AbstractEventLoop, context: Dict[str, Any]) -> None:
    """Handle uncaught exceptions in the event loop."""
    exception = context.get('exception', context['message'])
    logger.error(f"Uncaught exception: {exception}", exc_info=exception if isinstance(exception, Exception) else None)
    
    # Schedule application shutdown
    if not loop.is_closed():
        loop.create_task(on_shutdown(None))

# Add health check endpoint - will be set in on_startup now
# app.router.add_get("/health", health_check) # REMOVED: Router setup moved to on_startup

# Setup startup and shutdown handlers
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

logger.info("Starting aiohttp web application...")
logger.info(f"Binding to port: {config.WEBAPP_PORT}")

def get_ssl_context() -> Optional[ssl.SSLContext]:
    """Create SSL context for webhook."""
    if not config.WEBHOOK_SSL_CERT or not config.WEBHOOK_SSL_PRIV:
        return None
    try:
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(config.WEBHOOK_SSL_CERT, config.WEBHOOK_SSL_PRIV)
        return ssl_context
    except Exception as e:
        logger.error(f"Failed to create SSL context: {e}", exc_info=True)
        return None

async def setup_bot_commands(bot: Bot) -> None:
    """Configure bot commands."""
    try:
        # Define commands for all users
        commands = [
            BotCommand(command="start", description="Начать работу с ботом"),
            BotCommand(command="help", description="Показать справку"),
            BotCommand(command="catalog", description="Просмотр каталога продукции"),
            BotCommand(command="search", description="Поиск по базе знаний"),
            BotCommand(command="tests", description="Доступные тесты"),
            BotCommand(command="profile", description="Мой профиль")
        ]
        
        # Add admin commands if user is admin
        admin_commands = [
            BotCommand(command="admin", description="Панель управления"),
            BotCommand(command="stats", description="Статистика использования"),
            BotCommand(command="users", description="Управление пользователями"),
            BotCommand(command="categories", description="Управление категориями"),
            BotCommand(command="settings", description="Настройки бота")
        ]
        
        # Set commands for all users
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        
        # Set admin commands for admin users
        for admin_id in config.ADMIN_IDS:
            await bot.set_my_commands(
                commands + admin_commands,
                scope=BotCommandScopeChat(chat_id=admin_id)
            )
        
        logger.info("Bot commands configured successfully")
    except Exception as e:
        logger.error(f"Error setting up bot commands: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        # Setup logging
        setup_logging()
        
        # Set up exception handler
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(handle_exception)
        
        # Get host and port
        run_host = config.WEBAPP_HOST
        run_port = config.WEBAPP_PORT
        if config.IS_PRODUCTION:
            run_host = '0.0.0.0'
            run_port = int(os.getenv('PORT', config.WEBAPP_PORT))  # Use PORT env variable in production
        
        # Run the application
        if config.ENABLE_WEBHOOK:
            # Use asyncio.run for the main entry point in webhook mode
            logger.info("Starting aiohttp web server with asyncio.run...")
            asyncio.run(web.run_app(
                app,
                host=run_host,
                port=run_port,
                ssl_context=get_ssl_context() if config.WEBHOOK_SSL_CERT else None
            ))
            logger.info("Web server stopped.")
        else:
            # In polling mode, we need to run the dispatcher directly
            logger.info("Starting bot in polling mode...")
            try:
                # Start polling in the background
                loop.create_task(dp.start_polling(
                    allowed_updates=["message", "callback_query", "inline_query"],
                    drop_pending_updates=True
                ))
                # Run the event loop
                loop.run_forever()
            except KeyboardInterrupt:
                logger.info("Received shutdown signal, stopping bot...")
            except Exception as e:
                logger.error(f"Error in polling mode: {e}", exc_info=True)
            finally:
                # Run cleanup
                loop.run_until_complete(on_shutdown(None))
                loop.close()
                logger.info("Bot stopped.")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        # Run cleanup in case of error
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(on_shutdown(None))
            else:
                loop.run_until_complete(on_shutdown(None))
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {cleanup_error}", exc_info=True)
        finally:
            if not loop.is_closed():
                loop.close()
            sys.exit(1)
