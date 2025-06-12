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

# Initialize bot
bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Initialize Dispatcher globally with storage
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
                db_file=config.DB_FILE,
                pool_size=config.DB_POOL_SIZE
            )
            await new_db_pool.initialize()
            logger.info("Database pool initialized successfully")

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

# Register our custom startup and shutdown handlers with the dispatcher
dp.startup.register(on_startup)
dp.shutdown.register(on_shutdown)

# Create web application
app = web.Application()

logger.info("Starting aiohttp web application...\n")
logger.info(f"Binding to port: {config.WEBAPP_PORT}\n")

if __name__ == "__main__":
    try:
        # Setup logging
        setup_logging()

        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Set up exception handler
        loop.set_exception_handler(handle_exception)

        # Get host and port
        run_host = '0.0.0.0' # Render requires binding to 0.0.0.0
        run_port = int(os.getenv('PORT', '8000')) # Fallback to 8000 if PORT env var is not set (unlikely on Render)

        # Run the application
        if config.ENABLE_WEBHOOK:
            logger.info("Starting aiohttp web server...")
            logger.info(f"Binding to host: {run_host}, port: {run_port}")

            webhook_host = os.getenv("WEBHOOK_HOST") or os.getenv("RENDER_EXTERNAL_URL")
            webhook_path = os.getenv("WEBHOOK_PATH", f"/webhook/{config.BOT_TOKEN}")

            if not webhook_host:
                logger.error("WEBHOOK_HOST or RENDER_EXTERNAL_URL environment variable is not set.")
                raise ValueError("WEBHOOK_HOST or RENDER_EXTERNAL_URL must be set in production.")

            # Log webhook configuration
            logger.info(f"Webhook host: {webhook_host}")
            logger.info(f"Webhook path: {webhook_path}")

            # Ensure webhook_host doesn't have protocol prefix
            if webhook_host.startswith("https://"):
                webhook_host = webhook_host[8:]
            elif webhook_host.startswith("http://"):
                webhook_host = webhook_host[7:]

            webhook_url = f"https://{webhook_host}{webhook_path}"
            logger.info(f"Full webhook URL: {webhook_url}")

            try:
                loop.run_until_complete(bot.set_webhook(url=webhook_url))
                logger.info("Webhook set successfully")
            except Exception as e:
                logger.error(f"Failed to set webhook: {e}")
                raise

            # Manually register webhook handler on application router
            async def aiogram_webhook_handler(request: web.Request):
                try:
                    update_json = await request.text()
                    logger.info(f"Received webhook update: {update_json}")
                    update = types.Update.model_validate_json(update_json)
                    logger.info(f"Parsed update: {update}")
                    await dp.feed_webhook_update(bot, update)
                    logger.info("Update processed successfully")
                    return web.Response(text="OK")
                except Exception as e:
                    logger.error(f"Error processing webhook update: {e}", exc_info=True)
                    raise

            app.router.add_post(webhook_path, aiogram_webhook_handler)

            # Health check handler setup
            # The metrics collector is initialized in on_startup, which is called by dp.startup.
            # So, at this point, after setup_application, we can assume on_startup has run and metrics are available.
            async def get_metrics_for_health_check():
                metrics_data = await dp.storage.get_data(key=STORAGE_KEYS['metrics_collector'])
                return metrics_data.get('metrics_collector') if metrics_data else None

            # Create a simple health check handler that retrieves metrics on demand
            async def health_check_wrapper(request: web.Request) -> web.Response:
                metrics_collector_instance = await get_metrics_for_health_check()
                if metrics_collector_instance:
                    handler = create_health_check_handler(metrics_collector_instance)
                    return await handler(request)
                else:
                    logger.warning("MetricsCollector not available for health check.")
                    return web.json_response({"status": "error", "message": "Metrics not initialized"}, status=500)

            app.router.add_get('/health', health_check_wrapper)

            try:
                web.run_app(
                    app,
                    host=run_host,
                    port=run_port,
                    ssl_context=get_ssl_context() if config.WEBHOOK_SSL_CERT else None,
                    loop=loop
                )
                logger.info("Web server stopped.") # This log indicates normal shutdown, not an error
            except Exception as e:
                logger.error(f"Error running web application: {e}", exc_info=True)
                raise
        else:
            # In polling mode, we need to run the dispatcher directly
            logger.info("Starting bot in polling mode...")
            try:
                loop.create_task(dp.start_polling(
                    bot,
                    allowed_updates=config.ALLOWED_UPDATES,
                    drop_pending_updates=True
                ))
                # Run the event loop
                logger.info("Bot in polling mode started. Running event loop forever.")
                loop.run_forever() # Keep the loop running for background tasks
            except KeyboardInterrupt:
                logger.info("Received shutdown signal, stopping bot...")
            except Exception as e:
                logger.error(f"Error in polling mode: {e}", exc_info=True)
            finally:
                logger.info("Polling mode cleanup completed.")
                # Close the event loop
                try:
                    if not loop.is_closed():
                        loop.close()
                        logger.info("Event loop closed in polling cleanup.")
                except Exception as loop_error:
                    logger.error(f"Error closing event loop: {loop_error}", exc_info=True)

    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)
