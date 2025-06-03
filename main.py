"""Main application module."""

import asyncio
import logging
import signal
import sys
from typing import Optional, Callable, Any, Awaitable
from functools import wraps

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import (
    BOT_TOKEN,
    WEBHOOK_HOST,
    WEBHOOK_PATH,
    WEBAPP_PORT,
    WEBHOOK_SSL_CERT,
    WEBHOOK_SSL_PRIV,
    ENABLE_WEBHOOK,
    ENABLE_METRICS,
    LOG_LEVEL,
    WEBHOOK_URL,
    ENVIRONMENT,
    IS_PRODUCTION
)
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

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info(f"Environment: {ENVIRONMENT}, IS_PRODUCTION: {IS_PRODUCTION}")

# Initialize bot and dispatcher
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Create web application
app = web.Application()

# Store webhook handler for cleanup
webhook_handler: Optional[SimpleRequestHandler] = None

async def setup_webhook(bot: Bot) -> None:
    """Configure webhook for the bot."""
    if not WEBHOOK_URL:
        logger.error("WEBHOOK_URL is not set. Cannot configure webhook.")
        return

    try:
        # Remove any existing webhook
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Deleted existing webhook")

        # Set new webhook
        await bot.set_webhook(
            url=WEBHOOK_URL,
            allowed_updates=["message", "callback_query", "inline_query"],
            drop_pending_updates=True
        )
        logger.info(f"Webhook set to {WEBHOOK_URL}")

        # Verify webhook
        webhook_info = await bot.get_webhook_info()
        logger.info(f"Webhook info: {webhook_info}")
    except Exception as e:
        logger.error(f"Failed to setup webhook: {e}")
        raise

@handle_errors
@log_operation
async def on_startup() -> None:
    """Initialize application on startup."""
    logger.info("Starting up application...")
    
    # Initialize resource manager
    await resource_manager.initialize()
    logger.info("Resource manager initialized")
    
    logger.info(f"ENABLE_WEBHOOK: {ENABLE_WEBHOOK}")
    
    # Start metrics collection if enabled
    if ENABLE_METRICS:
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
    from handlers import (
        register_user_handlers,
        register_catalog_handlers,
        register_test_handlers,
        register_admin_handlers
    )
    
    register_user_handlers(dp)
    register_catalog_handlers(dp)
    register_test_handlers(dp)
    register_admin_handlers(dp)
    logger.info("Handlers registered")
    
    # Setup webhook if enabled
    if ENABLE_WEBHOOK:
        if not WEBHOOK_URL:
            raise ValueError("WEBHOOK_URL is required when webhook mode is enabled")
            
        logger.info(f"Attempting to setup webhook with URL: {WEBHOOK_URL}")
        
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
        webhook_handler.register(app, path=WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        logger.info(f"Webhook server configured at {WEBHOOK_URL}")
    else:
        # Start polling
        await dp.start_polling(bot)
        logger.info("Bot started in polling mode")

@handle_errors
@log_operation
async def on_shutdown() -> None:
    """Cleanup on shutdown."""
    logger.info("Shutting down application...")
    
    # Stop metrics collection
    if ENABLE_METRICS:
        metrics_collector.stop()
        logger.info("Metrics collection stopped")
    
    # Stop webhook if running
    if webhook_handler:
        await webhook_handler.shutdown()
        logger.info("Webhook server stopped")
    
    # Cleanup resources
    await resource_manager.cleanup()
    logger.info("Resource cleanup completed")
    
    # Close bot session
    await bot.session.close()
    logger.info("Bot session closed")

async def health_check(request: web.Request) -> web.Response:
    """Health check endpoint."""
    try:
        # Get metrics if enabled
        if ENABLE_METRICS:
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

def handle_exception(loop: asyncio.AbstractEventLoop, context: dict) -> None:
    """Handle uncaught exceptions."""
    msg = context.get("exception", context["message"])
    logger.error(f"Uncaught exception: {msg}", exc_info=context.get("exception"))
    
    # Record error in metrics if enabled
    if ENABLE_METRICS:
        metrics_collector.increment_error_count("uncaught_exception")

# Add health check endpoint
app.router.add_get("/health", health_check)

# Setup startup and shutdown handlers
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

# Setup exception handler
try:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
except RuntimeError:
    loop = asyncio.get_running_loop()

loop.set_exception_handler(handle_exception)

# Add signal handlers
for sig in (signal.SIGTERM, signal.SIGINT):
    loop.add_signal_handler(
        sig,
        lambda: asyncio.create_task(on_shutdown())
    )

if __name__ == "__main__":
    # Start the application
    web.run_app(
        app,
        host="0.0.0.0",
        port=WEBAPP_PORT,
        ssl_context={
            'cert': WEBHOOK_SSL_CERT,
            'key': WEBHOOK_SSL_PRIV
        } if WEBHOOK_SSL_CERT and WEBHOOK_SSL_PRIV else None
    )
