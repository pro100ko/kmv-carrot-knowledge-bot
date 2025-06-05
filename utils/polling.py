"""Polling mode setup for the bot."""

import logging
from aiogram import Dispatcher
from aiogram.enums import ParseMode

logger = logging.getLogger(__name__)

async def setup_polling(dp: Dispatcher) -> None:
    """Configure polling mode for the bot.
    
    Args:
        dp: The bot's dispatcher instance
    """
    try:
        # Start polling
        await dp.start_polling(
            allowed_updates=["message", "callback_query", "inline_query"],
            drop_pending_updates=True
        )
        logger.info("Bot started in polling mode")
    except Exception as e:
        logger.error(f"Error starting polling: {e}", exc_info=True)
        raise 