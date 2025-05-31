import logging
import os
import sys
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

print("[BOOT] main.py started")

# Get environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "8000"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

if not BOT_TOKEN:
    print("[ERROR] BOT_TOKEN is not set!")
    sys.exit(1)
if not RENDER_EXTERNAL_URL:
    print("[ERROR] RENDER_EXTERNAL_URL is not set! Set it to your Render public URL (without trailing slash)")
    sys.exit(1)

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"
print(f"[BOOT] Using PORT={PORT}, WEBHOOK_URL={WEBHOOK_URL}")

# Create bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Register /start handler for all text messages
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    print(f"[HANDLER] /start from {message.from_user.id}")
    await message.answer("Hello! The bot is running via webhook.")

# Create a keyboard with a /start button
start_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="/start")]],
    resize_keyboard=True,
    one_time_keyboard=False
)

# Handler to remove the keyboard
@dp.message(Command("remove_keyboard"))
async def remove_keyboard_handler(message: types.Message):
    await message.answer("Keyboard removed.", reply_markup=ReplyKeyboardRemove())

# Catch-all handler for all messages
@dp.message()
async def catch_all_handler(message: types.Message):
    print(f"[CATCH-ALL] Received message: {message}")
    print(f"[CATCH-ALL] message.text: {message.text}")
    if message.text == "/start":
        await message.answer("Hello! The bot is running via webhook.", reply_markup=start_keyboard)
    elif message.text == "/remove_keyboard":
        await message.answer("Keyboard removed.", reply_markup=ReplyKeyboardRemove())
    else:
        # Add more button text logic here if needed
        await message.answer(f"Echo: {message.text}", reply_markup=start_keyboard)

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

# Webhook handler
async def webhook_handler(request):
    print("[HTTP] /webhook POST received")
    try:
        update = types.Update.model_validate(await request.json())
        print(f"[UPDATE] {update}")
        await dp.feed_update(bot, update)
    except Exception as e:
        print(f"[ERROR] Webhook handler: {e}")
    return web.Response(text="OK")
app.router.add_post(WEBHOOK_PATH, webhook_handler)

# Startup
async def on_startup(app):
    print("[STARTUP] App startup - setting webhook...")
    await bot.set_webhook(WEBHOOK_URL)
    print(f"[STARTUP] Webhook set to {WEBHOOK_URL}")
app.on_startup.append(on_startup)

# Shutdown
async def on_shutdown(app):
    print("[SHUTDOWN] App shutdown - deleting webhook and closing bot session...")
    await bot.delete_webhook()
    await bot.session.close()
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    print("[MAIN] Starting aiohttp web server...")
    web.run_app(app, host="0.0.0.0", port=PORT)
