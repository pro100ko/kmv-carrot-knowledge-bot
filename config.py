import os
import json
from typing import List, Dict, Any

# Environment settings
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

# Токен бота и ID администраторов
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8127758206:AAErKt-s-ztq3xgu5M9sqP2esZWyhowXvNI")
ADMIN_USER_IDS = [int(id) for id in os.environ.get("ADMIN_USER_IDS", "340877389").split()]

# Настройки webhook (для размещения на хостинге)
WEBHOOK_HOST = os.environ.get("WEBHOOK_URL", "https://kmv-carrot-knowledge-bot.onrender.com")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Настройки SQLite
DB_FILE = "morkovka_bot.db"
SQLITE_AVAILABLE = False  # Будет установлено в True, если SQLite успешно инициализирован

# Основные категории товаров
PRODUCT_CATEGORIES = [
    "Зелень", "Сезонный стол", "Основная витрина", "Холодильная горка", 
    "Экзотика", "Ягоды", "Орехи/сухофрукты", "Бакалея", "Бар"
]

# Настройки поиска
MIN_SEARCH_LENGTH = 3  # Минимальная длина запроса для поиска
MAX_SEARCH_RESULTS = 10  # Максимальное количество результатов поиска
