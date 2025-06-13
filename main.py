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
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat, Update
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

load_dotenv() # Load environment variables from .env file

import config
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
from utils.polling import setup_polling
from utils.health_check import create_health_check_handler
from monitoring.metrics import MetricsCollector
from utils.error_handling import handle_errors, log_operation
from utils.resource_manager import resource_manager
import sqlite_db

# Get the configuration instance
app_config = config.get_config()

# Import handler setup functions
from handlers.user import setup_user_handlers
from handlers.catalog import setup_catalog_handlers
from handlers.tests import setup_test_handlers
from handlers.admin import setup_admin_handlers

# Configure logging
logging.basicConfig(
    level=app_config.LOG_LEVEL,
    format=app_config.LOG_FORMAT,
    filename=app_config.LOG_FILE if app_config.is_production() else None
)
logger = logging.getLogger(__name__)

logger.info(f"Environment: {app_config.ENVIRONMENT}, IS_PRODUCTION: {app_config.is_production()}")

# Initialize bot
bot = Bot(
    token=app_config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Initialize Dispatcher with storage
dp = Dispatcher(storage=MemoryStorage())

# Define storage keys
STORAGE_KEYS = {
    'db_pool': 'db_pool',
    'metrics_collector': 'metrics_collector'
}

async def on_startup(bot: Bot, dispatcher: Dispatcher) -> None:
    """Initialize application resources and start services."""
    logger.info("Entering on_startup function.")
    try:
        logger.info("Starting up application...")

        # Initialize database pool
        logger.info("Initializing database pool...")
        try:
            new_db_pool = DatabasePool(
                db_file=app_config.DB_FILE,
                pool_size=app_config.DB_POOL_SIZE
            )
            await new_db_pool.initialize()
            logger.info("Database pool initialized successfully")
            logger.info(f"Database file path: {app_config.DB_FILE}")

            # Store db_pool in storage
            logger.info("Storing database pool in dispatcher storage...")
            await dispatcher.storage.set_data(
                key=STORAGE_KEYS['db_pool'],
                data={'db_pool': new_db_pool}
            )
            logger.info("Database pool stored in dispatcher storage")

            # Initialize sqlite_db with the new pool
            logger.info("Initializing sqlite_db with the new pool...")
            sqlite_db.initialize(new_db_pool)
            logger.info("sqlite_db initialized with the new pool")

            # Initialize database and run migrations
            logger.info("Initializing database and running migrations...")
            await sqlite_db.db.initialize()
            logger.info("Database initialized and migrations completed successfully")

            # Verify database connection
            logger.info("Verifying database connection...")
            test_user = await sqlite_db.db.get_user(1)  # Try to get a test user
            logger.info("Database connection verified successfully")

        except Exception as db_error:
            logger.error(f"Database initialization failed: {db_error}", exc_info=True)
            raise RuntimeError(f"Database initialization failed: {db_error}")

        # Initialize metrics collector
        logger.info("Initializing metrics collector...")
        try:
            metrics = MetricsCollector()
            await dispatcher.storage.set_data(
                key=STORAGE_KEYS['metrics_collector'],
                data={'metrics_collector': metrics}
            )
            logger.info("Metrics collector initialized and stored")
        except Exception as metrics_error:
            logger.error(f"Metrics collector initialization failed: {metrics_error}", exc_info=True)
            raise RuntimeError(f"Metrics collector initialization failed: {metrics_error}")

        # Register middleware
        logger.info("Registering middleware...")
        try:
            dispatcher.update.middleware(MetricsMiddleware())
            dispatcher.update.middleware(ErrorHandlingMiddleware())
            dispatcher.update.middleware(StateManagementMiddleware())
            dispatcher.update.middleware(LoggingMiddleware())
            dispatcher.update.middleware(AdminAccessMiddleware())
            dispatcher.update.middleware(UserActivityMiddleware())
            dispatcher.update.middleware(RateLimitMiddleware())
            logger.info("All middleware registered successfully")
        except Exception as middleware_error:
            logger.error(f"Middleware registration failed: {middleware_error}", exc_info=True)
            raise RuntimeError(f"Middleware registration failed: {middleware_error}")

        # Setup bot commands
        logger.info("Setting up bot commands...")
        try:
            await setup_bot_commands(bot)
            logger.info("Bot commands configured successfully")
        except Exception as commands_error:
            logger.error(f"Bot commands setup failed: {commands_error}", exc_info=True)
            raise RuntimeError(f"Bot commands setup failed: {commands_error}")

        # Setup handlers
        logger.info("Setting up handlers...")
        try:
            logger.info("Setting up user handlers...")
            setup_user_handlers(dispatcher)
            logger.info("User handlers registered")
            
            logger.info("Setting up catalog handlers...")
            setup_catalog_handlers(dispatcher)
            logger.info("Catalog handlers registered")
            
            logger.info("Setting up test handlers...")
            setup_test_handlers(dispatcher)
            logger.info("Test handlers registered")
            
            logger.info("Setting up admin handlers...")
            setup_admin_handlers(dispatcher)
            logger.info("Admin handlers registered")
        except Exception as handlers_error:
            logger.error(f"Handlers setup failed: {handlers_error}", exc_info=True)
            raise RuntimeError(f"Handlers setup failed: {handlers_error}")

        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Critical error during startup: {e}", exc_info=True)
        raise RuntimeError(f"Application startup failed: {e}")

async def on_shutdown(bot: Bot, dispatcher: Dispatcher) -> None:
    """Cleanup application resources."""
    logger.info("Starting application shutdown...")
    try:
        # Get resources from storage (expecting them wrapped in a dictionary)
        db_pool_data = await dispatcher.storage.get_data(key=STORAGE_KEYS['db_pool'])
        db_pool = db_pool_data.get('db_pool') if db_pool_data else None

        metrics_data = await dispatcher.storage.get_data(key=STORAGE_KEYS['metrics_collector'])
        metrics = metrics_data.get('metrics_collector') if metrics_data else None

        # Cleanup database pool
        if db_pool:
            try:
                await db_pool.close()
                logger.info("Database pool closed")
            except Exception as e:
                logger.error(f"Error closing database pool: {e}")

        # Cleanup metrics
        if metrics:
            try:
                await metrics.cleanup()
                logger.info("Metrics collector cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up metrics: {e}")

        # Close bot session
        if bot and bot.session and not bot.session.closed:
            try:
                await bot.session.close()
                logger.info("Bot session closed")
            except Exception as e:
                logger.error(f"Error closing bot session during shutdown: {e}")

        logger.info("Application shutdown completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
        raise

def handle_exception(loop: asyncio.AbstractEventLoop, context: Dict[str, Any]) -> None:
    """Handle uncaught exceptions in the event loop."""
    exception = context.get('exception', context['message'])
    logger.error(f"Uncaught exception: {exception}", exc_info=exception if isinstance(exception, Exception) else None)

    # The dispatcher's shutdown handlers will be called by aiogram's integration with aiohttp
    # for webhook mode, and explicitly in polling mode's finally block.
    # No need to manually schedule on_shutdown here.

def get_ssl_context() -> Optional[ssl.SSLContext]:
    """Create SSL context for webhook."""
    if not app_config.WEBHOOK_SSL_CERT or not app_config.WEBHOOK_SSL_PRIV:
        return None
    try:
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(app_config.WEBHOOK_SSL_CERT, app_config.WEBHOOK_SSL_PRIV)
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
        for admin_id in app_config.ADMIN_IDS:
            await bot.set_my_commands(
                commands + admin_commands,
                scope=BotCommandScopeChat(chat_id=admin_id)
            )

        logger.info("Bot commands configured successfully")
    except Exception as e:
        logger.error(f"Error setting up bot commands: {e}", exc_info=True)
        raise

# Register our custom startup and shutdown handlers with the dispatcher
dp.startup.register(on_startup)
dp.shutdown.register(on_shutdown)

# Create web application
app = web.Application()

logger.info("Starting aiohttp web application...\n")
logger.info(f"Binding to port: {app_config.PORT}\n")

async def setup_webhook_and_run_app(bot: Bot, dp: Dispatcher):
    """Sets up the webhook and runs the aiohttp application."""
    # Use globally defined bot and dp instances

    logger.info("Starting aiohttp web server...")
    logger.info(f"Binding to host: {app_config.HOST}, port: {app_config.PORT}")

    if not app_config.WEBHOOK_HOST:
        logger.error("WEBHOOK_HOST or RENDER_EXTERNAL_URL environment variable is not set.")
        raise ValueError("WEBHOOK_HOST or RENDER_EXTERNAL_URL must be set in production.")

    # Ensure webhook_host doesn't have protocol prefix
    webhook_host = app_config.WEBHOOK_HOST
    if webhook_host.startswith("https://"):
        webhook_host = webhook_host[8:]
    elif webhook_host.startswith("http://"):
        webhook_host = webhook_host[7:]

    # Use a fixed webhook path without the bot token
    webhook_path = "/webhook"
    webhook_url = f"https://{webhook_host}{webhook_path}"
    logger.info(f"Full webhook URL: {webhook_url}")

    try:
        # Create an instance of SimpleRequestHandler and register it with the aiohttp application
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            secret_token=app_config.WEBHOOK_SECRET,
        )
        webhook_requests_handler.register(app, path=webhook_path)
        logger.info("Webhook handler setup completed")

        # Mount dispatcher startup and shutdown hooks to aiohttp application
        setup_application(app, dp, bot=bot)
        logger.info("Application startup handlers mounted")

        # Add a health check handler at the root path
        async def root_handler(request):
            return web.Response(text="Bot is running", status=200)
        app.router.add_get('/', root_handler)
        logger.info("Root handler added")

        # Add health check handler if enabled
        if app_config.ENABLE_HEALTH_CHECK:
            try:
                metrics_data = await dp.storage.get_data(key=STORAGE_KEYS['metrics_collector'])
                metrics_collector = metrics_data.get('metrics_collector') if metrics_data else None
                if metrics_collector:
                    app.router.add_get('/health', create_health_check_handler(metrics_collector))
                    logger.info("Health check handler added")
                else:
                    logger.warning("Metrics collector not found in storage, health check handler not added")
            except Exception as metrics_error:
                logger.warning(f"Could not setup health check handler: {metrics_error}")

        # Set webhook for the bot
        logger.info(f"Setting webhook to: {webhook_url}")
        await bot.set_webhook(
            url=webhook_url,
            allowed_updates=app_config.ALLOWED_UPDATES,
            secret_token=app_config.WEBHOOK_SECRET,
        )
        logger.info("Webhook set successfully")
        webhook_info = await bot.get_webhook_info()
        logger.info(f"Webhook info: {webhook_info}")

        # Start the aiohttp web server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, app_config.HOST, app_config.PORT)
        await site.start()
        logger.info("aiohttp web server started")

        # Keep the application running until interrupted
        # This line is crucial for keeping the aiohttp server alive
        await asyncio.Event().wait()

    except Exception as e:
        logger.critical(f"Critical error during application startup: {e}", exc_info=True)
        await on_shutdown(bot, dp) # Ensure cleanup on critical error
        raise # Re-raise the exception to terminate the process

if __name__ == "__main__":
    try:
        # Setup logging
        setup_logging()

        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Set up exception handler
        loop.set_exception_handler(handle_exception)

        # Run the application
        if app_config.ENABLE_WEBHOOK:
            try:
                loop.run_until_complete(setup_webhook_and_run_app(bot, dp)) # Pass global bot and dp
            except Exception as e:
                logger.error(f"Error in webhook mode: {e}", exc_info=True)
                # Try to cleanup on error
                try:
                    loop.run_until_complete(on_shutdown(bot, dp))
                except Exception as shutdown_error:
                    logger.error(f"Error during shutdown: {shutdown_error}")
                raise
        elif app_config.ENABLE_POLLING:
            # In polling mode, we need to run the dispatcher directly
            logger.info("Starting bot in polling mode...")
            try:
                # Run startup handlers first
                loop.run_until_complete(on_startup(bot, dp))
                
                # Then start polling
                loop.create_task(dp.start_polling(
                    bot,
                    allowed_updates=app_config.ALLOWED_UPDATES,
                    drop_pending_updates=True
                ))
                # Run the event loop
                logger.info("Bot in polling mode started. Running event loop forever.")
                loop.run_forever()
            except KeyboardInterrupt:
                logger.info("Received shutdown signal, stopping bot...")
            except Exception as e:
                logger.error(f"Error in polling mode: {e}", exc_info=True)
            finally:
                logger.info("Polling mode cleanup completed.")
                # Run shutdown handlers
                try:
                    loop.run_until_complete(on_shutdown(bot, dp))
                except Exception as shutdown_error:
                    logger.error(f"Error during shutdown: {shutdown_error}")
                # Close the event loop
                try:
                    if not loop.is_closed():
                        loop.close()
                        logger.info("Event loop closed in polling cleanup.")
                except Exception as loop_error:
                    logger.error(f"Error closing event loop: {loop_error}", exc_info=True)
        else:
            raise RuntimeError("Neither webhook nor polling mode is enabled")

    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)
