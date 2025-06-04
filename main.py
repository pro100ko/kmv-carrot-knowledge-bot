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

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
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
from middleware import (
    metrics_middleware,
    error_handling_middleware,
    state_management_middleware,
    logging_middleware,
    AdminAccessMiddleware,
    UserActivityMiddleware,
    RateLimitMiddleware
)
from monitoring.metrics import metrics_collector
from utils.error_handling import handle_errors, log_operation
from utils.resource_manager import resource_manager

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

async def setup_webhook(bot: Bot) -> None:
    """Configure webhook for the bot."""
    if not config.WEBHOOK_URL:
        logger.error("WEBHOOK_URL is not set. Cannot configure webhook.")
        return

    try:
        # Remove any existing webhook
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Deleted existing webhook")

        # Set new webhook
        await bot.set_webhook(
            url=config.WEBHOOK_URL,
            allowed_updates=["message", "callback_query", "inline_query"],
            drop_pending_updates=True
        )
        logger.info(f"Webhook set to {config.WEBHOOK_URL}")

        # Verify webhook
        webhook_info = await bot.get_webhook_info()
        logger.info(f"Webhook info: {webhook_info}")
    except Exception as e:
        logger.error(f"Failed to setup webhook: {e}")
        raise

async def on_startup() -> None:
    """Initialize application on startup."""
    logger.info("Entering on_startup function.")
    logger.info("Starting up application...")
    
    # Add db_pool to globals to ensure it's available in shutdown
    globals()['db_pool'] = db_pool

    # Initialize resource manager
    await resource_manager.initialize()
    logger.info("Resource manager initialized")
    
    logger.info(f"ENABLE_WEBHOOK: {config.ENABLE_WEBHOOK}")
    
    # Start metrics collection if enabled
    if config.ENABLE_METRICS:
        metrics_collector.start()
        logger.info("Metrics collection started")
    
    # Register middleware
    dp.update.middleware(metrics_middleware)
    dp.update.middleware(error_handling_middleware)
    dp.update.middleware(state_management_middleware)
    dp.update.middleware(logging_middleware)
    dp.update.middleware(AdminAccessMiddleware())
    dp.update.middleware(UserActivityMiddleware())
    dp.update.middleware(RateLimitMiddleware())
    logger.info("Middleware registered")
    
    # Register handlers
    setup_user_handlers(dp)
    setup_catalog_handlers(dp)
    setup_test_handlers(dp)
    setup_admin_handlers(dp)
    logger.info("Handlers registered")
    
    # Setup webhook if enabled
    if config.ENABLE_WEBHOOK:
        if not config.WEBHOOK_URL:
            raise ValueError("WEBHOOK_URL is required when webhook mode is enabled")
            
        logger.info(f"Attempting to setup webhook with URL: {config.WEBHOOK_URL}")
        
        # Configure webhook in Telegram
        await setup_webhook(bot)
        
        logger.info("Webhook setup function called.")
        
        # Setup webhook handler
        global webhook_handler
        webhook_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            handle_signals=False
        )
        
        # Register webhook handler with the correct path
        webhook_handler.register(app, path=config.WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        logger.info(f"Webhook server configured at {config.WEBHOOK_URL}")
    else:
        # Start polling
        await dp.start_polling(bot)
        logger.info("Bot started in polling mode")

async def on_shutdown() -> None:
    """Cleanup on shutdown."""
    logger.info("Shutting down application...")
    
    try:
        # Stop metrics collection first
        if config.ENABLE_METRICS:
            await metrics_collector.cleanup()
            logger.info("Metrics collection stopped")
        
        # Stop webhook if running
        if webhook_handler:
            await webhook_handler.shutdown()
            logger.info("Webhook server stopped")
        
        # Cleanup database pool
        await db_pool.cleanup()
        logger.info("Database pool cleaned up")
        
        # Cleanup other resources
        await resource_manager.cleanup()
        logger.info("Resource cleanup completed")
        
        # Close bot session last
        await bot.session.close()
        logger.info("Bot session closed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)
    finally:
        logger.info("Application shutdown completed")

def handle_exception(loop: asyncio.AbstractEventLoop, context: Dict[str, Any]) -> None:
    """Handle uncaught exceptions in the event loop."""
    exception = context.get('exception', context['message'])
    logger.error(f"Uncaught exception: {exception}", exc_info=exception if isinstance(exception, Exception) else None)
    
    # Schedule application shutdown
    if not loop.is_closed():
        loop.create_task(on_shutdown())

async def health_check(request: web.Request) -> web.Response:
    """Health check endpoint."""
    try:
        # Get metrics if enabled
        if config.ENABLE_METRICS:
            metrics = metrics_collector.get_metrics()
            return web.json_response({
                "status": "healthy",
                "metrics": metrics
            })
        return web.json_response({"status": "healthy"})
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return web.json_response(
            {"status": "unhealthy", "error": str(e)},
            status=500
        )

# Add health check endpoint
app.router.add_get("/health", health_check)

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

if __name__ == "__main__":
    try:
        # Set up exception handler
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(handle_exception)
        
        # Register signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(on_shutdown()))
        
        # Determine host and port based on environment
        run_host = config.WEBAPP_HOST
        run_port = config.WEBAPP_PORT
        if config.IS_PRODUCTION:
            run_host = '0.0.0.0'
            run_port = int(os.getenv('PORT', config.WEBAPP_PORT)) # Use PORT env variable in production

        # Run the application
        if config.ENABLE_WEBHOOK:
            web.run_app(
                app,
                host=run_host,
                port=run_port,
                ssl_context=get_ssl_context() if config.WEBHOOK_SSL_CERT else None
            )
        else:
            # In polling mode, register on_startup with the dispatcher
            dp.startup_handlers.append(on_startup)
            loop.run_until_complete(dp.start_polling(bot))
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        loop.run_until_complete(on_shutdown())
    finally:
        loop.close()
