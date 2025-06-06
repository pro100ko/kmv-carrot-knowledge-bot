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

load_dotenv() # Load environment variables from .env file

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

async def on_startup(runner_instance: web.Application) -> None:
    """Initialize application resources and start services."""
    logger.info("Entering on_startup function.")
    try:
        logger.info("Starting up application...")

        # Initialize database pool
        new_db_pool = DatabasePool(
            db_file=config.DB_FILE,
            pool_size=config.DB_POOL_SIZE
        )
        await new_db_pool.initialize()  # Initialize the pool first

        # Store db_pool in the aiohttp application instance
        runner_instance['db_pool'] = new_db_pool
        # Also store in dp.data for potential handler access patterns
        dp.data['db_pool'] = new_db_pool

        # Initialize sqlite_db with the new pool
        sqlite_db.initialize(new_db_pool)
        await sqlite_db.db.initialize()  # Initialize the database instance

        # Initialize metrics collector
        metrics = MetricsCollector()
        metrics.start()

        # Store metrics_collector in the aiohttp application instance
        runner_instance['metrics_collector'] = metrics
        # Also store in dp.data for potential handler access patterns
        dp.data['metrics_collector'] = metrics

        # Create and store health check handler
        health_check_handler = create_health_check_handler(metrics)
        runner_instance['health_check_handler'] = health_check_handler
        runner_instance.router.add_get('/health', health_check_handler)

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
            logger.info("Setting up webhook in production mode...")
            # Get webhook details directly from environment variables
            webhook_host = os.getenv("WEBHOOK_HOST") or os.getenv("RENDER_EXTERNAL_URL")
            # Use config.BOT_TOKEN here as it should be loaded by now
            webhook_path = os.getenv("WEBHOOK_PATH", f"/webhook/{config.BOT_TOKEN}")
            
            if not webhook_host:
                 logger.error("WEBHOOK_HOST or RENDER_EXTERNAL_URL environment variable is not set. Cannot set up webhook.")
                 # Depending on desired behavior, could raise an error or fallback to polling
                 # For now, raising an error to be explicit about the configuration issue
                 raise ValueError("WEBHOOK_HOST or RENDER_EXTERNAL_URL must be set in production.")

            webhook_url = f"https://{webhook_host}{webhook_path}" if webhook_host else None
            
            logger.info(f"Webhook Host: {webhook_host}")
            logger.info(f"Webhook Path: {webhook_path}")
            logger.info(f"Constructed Webhook URL: {webhook_url}")

            if not webhook_url:
                logger.error("Constructed WEBHOOK_URL is None. Cannot set up webhook.")
                 # Optionally, raise an error or switch to polling
                raise ValueError("Constructed WEBHOOK_URL is None.")

            await setup_webhook(bot, dp, webhook_url, webhook_path)
            logger.info("Webhook setup attempted.")
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

async def on_shutdown(runner_instance: web.Application) -> None:
    """Clean up application resources."""
    logger.info("Entering on_shutdown function.")
    try:
        logger.info("Shutting down application...")

        # Stop metrics collection - retrieve from aiohttp app instance
        metrics_collector = runner_instance.get('metrics_collector')
        if metrics_collector:
            await metrics_collector.cleanup()  # Use cleanup instead of stop to ensure proper cleanup
            logger.info("Metrics collection stopped")

        # Stop webhook if running (assuming webhook_handler is stored globally or in app instance if needed)
        # For now, relying on global webhook_handler as per current code structure
        global webhook_handler
        if webhook_handler:
            # Check if webhook_handler has a shutdown method before calling
            if hasattr(webhook_handler, 'shutdown') and callable(webhook_handler.shutdown):
                await webhook_handler.shutdown()
                logger.info("Webhook server stopped")
            else:
                logger.warning("webhook_handler does not have a shutdown method.")

        # Close database pool - retrieve from aiohttp app instance
        db_pool_instance = runner_instance.get('db_pool')
        if db_pool_instance:
            await db_pool_instance.close()
            logger.info("Database pool closed")

        # Close bot session
        # Assuming 'bot' is accessible globally or via runner_instance if needed
        # For now, relying on global 'bot' as per current code structure
        if 'bot' in globals() and hasattr(bot, 'session') and hasattr(bot.session, 'close'):
             await bot.session.close()
             logger.info("Bot session closed")
        else:
             logger.warning("Bot or bot session not available for closing during shutdown.")

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
                logger.info("Starting polling mode cleanup...")

                # Access instances from dp.data (used bot.data previously but it caused AttributeError)
                db_pool_instance = dp.data.get('db_pool')
                metrics_collector_instance = dp.data.get('metrics_collector')

                # Explicitly close db_pool if it was created
                if db_pool_instance:
                    try:
                        # Use the existing loop to run the async cleanup
                        loop.run_until_complete(db_pool_instance.close())
                        logger.info("Database pool closed in polling cleanup")
                    except Exception as db_cleanup_error:
                        logger.error(f"Error closing db_pool in polling finally: {db_cleanup_error}", exc_info=True)

                # Explicitly stop metrics collector if it was created
                if metrics_collector_instance:
                    try:
                         # Use the existing loop to run the async cleanup
                        loop.run_until_complete(metrics_collector_instance.cleanup())
                        logger.info("Metrics collector stopped in polling cleanup")
                    except Exception as metrics_cleanup_error:
                        logger.error(f"Error stopping metrics collector in polling finally: {metrics_cleanup_error}", exc_info=True)

                # Explicitly close bot session
                if bot and bot.session and not bot.session.closed:
                    try:
                        loop.run_until_complete(bot.session.close())
                        logger.info("Bot session closed in polling cleanup")
                    except Exception as bot_cleanup_error:
                        logger.error(f"Error closing bot session in polling finally: {bot_cleanup_error}", exc_info=True)

                # Close the event loop
                if not loop.is_closed():
                    loop.close()
                    logger.info("Event loop closed in polling cleanup.")

                logger.info("Polling mode cleanup completed.")

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
            # Explicitly close db_pool if it was created
            db_pool_instance = dp.data.get('db_pool')
            if db_pool_instance:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(db_pool_instance.close())
                    else:
                        loop.run_until_complete(db_pool_instance.close())
                except Exception as db_cleanup_error:
                    logger.error(f"Error closing db_pool in final cleanup: {db_cleanup_error}", exc_info=True)
            
            if not loop.is_closed():
                loop.close()
            sys.exit(1)
