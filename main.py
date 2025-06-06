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

# Initialize bot
bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

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
        await new_db_pool.initialize()

        # Store db_pool in the application instance
        runner_instance['db_pool'] = new_db_pool

        # Initialize sqlite_db with the new pool
        sqlite_db.initialize(new_db_pool)
        
        # Initialize database and run migrations
        try:
            await sqlite_db.db.initialize()
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            # Don't close the pool here, let the cleanup handle it
            raise

        # Initialize metrics collector
        metrics = MetricsCollector()
        runner_instance['metrics_collector'] = metrics

        # Create and store health check handler
        health_check_handler = create_health_check_handler(metrics)
        runner_instance['health_check_handler'] = health_check_handler
        runner_instance.router.add_get('/health', health_check_handler)

        # Create Dispatcher and Application
        dp = Dispatcher()
        aiogram_application = dp.to_app(
            bot=bot,
            middleware=[
                MetricsMiddleware(metrics),
                ErrorHandlingMiddleware(),
                StateManagementMiddleware(),
                LoggingMiddleware(),
                AdminAccessMiddleware(),
                UserActivityMiddleware(),
                RateLimitMiddleware(),
            ],
        )

        # Store resources in bot_data
        aiogram_application.bot_data['db_pool'] = new_db_pool
        aiogram_application.bot_data['metrics_collector'] = metrics

        logger.info("Middleware registered")

        # Setup webhook or polling based on environment
        if config.IS_PRODUCTION:
            logger.info("Setting up webhook in production mode...")
            webhook_host = os.getenv("WEBHOOK_HOST") or os.getenv("RENDER_EXTERNAL_URL")
            webhook_path = os.getenv("WEBHOOK_PATH", f"/webhook/{config.BOT_TOKEN}")
            
            if not webhook_host:
                logger.error("WEBHOOK_HOST or RENDER_EXTERNAL_URL environment variable is not set.")
                raise ValueError("WEBHOOK_HOST or RENDER_EXTERNAL_URL must be set in production.")

            webhook_url = f"https://{webhook_host}{webhook_path}"
            await bot.set_webhook(url=webhook_url)

            # Create SimpleRequestHandler and setup aiohttp application
            request_handler = SimpleRequestHandler(
                dispatcher=dp,
                bot=bot, # Pass bot to handler
                handle_in_background=True,
            )
            request_handler.register(runner_instance.router, path=webhook_path)
            # setup_application(runner_instance, aiogram_application) # This might overwrite routes, let's register handler manually for now
            logger.info("Webhook setup completed.")
        else:
            await setup_polling(application)

        # Setup bot commands
        await setup_bot_commands(bot)

        # Setup handlers
        setup_user_handlers(dp)
        setup_catalog_handlers(dp)
        setup_test_handlers(dp)
        setup_admin_handlers(dp)

        # Store application in runner instance
        runner_instance['aiogram_application'] = aiogram_application # Store aiogram application

        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
        raise

async def on_shutdown(runner_instance: web.Application) -> None:
    """Cleanup application resources."""
    logger.info("Starting application shutdown...")
    try:
        # Get resources from application
        db_pool = runner_instance.get('db_pool') if runner_instance else None
        metrics = runner_instance.get('metrics_collector') if runner_instance else None

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

        logger.info("Application shutdown completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
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
        
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Set up exception handler
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
            try:
                asyncio.run(web.run_app(
                    app,
                    host=run_host,
                    port=run_port,
                    ssl_context=get_ssl_context() if config.WEBHOOK_SSL_CERT else None
                ))
                logger.info("Web server stopped.")
            except Exception as e:
                logger.error(f"Error running web application: {e}", exc_info=True)
                raise
        else:
            # In polling mode, we need to run the dispatcher directly
            logger.info("Starting bot in polling mode...")
            try:
                # Create dispatcher
                dp = Dispatcher()
                
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
                try:
                    # Get resources from application
                    db_pool_instance = app.get('db_pool')
                    metrics_collector_instance = app.get('metrics_collector')

                    # Cleanup resources
                    if db_pool_instance:
                        try:
                            loop.run_until_complete(db_pool_instance.close())
                            logger.info("Database pool closed in polling cleanup")
                        except Exception as db_cleanup_error:
                            logger.error(f"Error closing db_pool in polling finally: {db_cleanup_error}", exc_info=True)

                    if metrics_collector_instance:
                        try:
                            loop.run_until_complete(metrics_collector_instance.cleanup())
                            logger.info("Metrics collector stopped in polling cleanup")
                        except Exception as metrics_cleanup_error:
                            logger.error(f"Error stopping metrics collector in polling finally: {metrics_cleanup_error}", exc_info=True)

                    # Close bot session
                    if bot and bot.session and not bot.session.closed:
                        try:
                            loop.run_until_complete(bot.session.close())
                            logger.info("Bot session closed in polling cleanup")
                        except Exception as bot_cleanup_error:
                            logger.error(f"Error closing bot session in polling finally: {bot_cleanup_error}", exc_info=True)

                except Exception as cleanup_error:
                    logger.error(f"Error during cleanup: {cleanup_error}", exc_info=True)
                finally:
                    # Close the event loop
                    try:
                        if not loop.is_closed():
                            loop.close()
                            logger.info("Event loop closed in polling cleanup.")
                    except Exception as loop_error:
                        logger.error(f"Error closing event loop: {loop_error}", exc_info=True)

                logger.info("Polling mode cleanup completed.")

    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)
