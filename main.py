import logging
import os
import sys
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

print("[BOOT] main.py started")

# Get environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "8000"))

if not BOT_TOKEN:
    print("[ERROR] BOT_TOKEN is not set!")
    sys.exit(1)

print(f"[BOOT] Using PORT={PORT}")

# Create bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Register /start handler
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    print(f"[HANDLER] /start from {message.from_user.id}")
    await message.answer("Hello! The bot is running.")

# Create aiohttp app
app = web.Application()

# Health check endpoint
async def health(request):
    print("[HTTP] /health requested")
    return web.Response(text="OK")
app.router.add_get("/health", health)

# Root endpoint
async def root(request):
    print("[HTTP] / requested")
    return web.Response(text="Bot server is running")
app.router.add_get("/", root)

# Webhook handler (not used, but required for aiogram+aiohttp)
async def webhook_handler(request):
    print("[HTTP] /webhook requested")
    return web.Response(text="Webhook not configured.")
app.router.add_post("/webhook", webhook_handler)

# Startup
async def on_startup(app):
    print("[STARTUP] App startup")
    # Start polling in background
    asyncio.create_task(dp.start_polling(bot))
app.on_startup.append(on_startup)

# Shutdown
async def on_shutdown(app):
    print("[SHUTDOWN] App shutdown")
    await bot.session.close()
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    print("[MAIN] Starting aiohttp web server...")
    web.run_app(app, host="0.0.0.0", port=PORT)
