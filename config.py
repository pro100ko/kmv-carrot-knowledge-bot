import os
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

# Environment settings
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# Webhook settings (for production)
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST") or os.getenv("RENDER_EXTERNAL_URL")  # Try both variables
if WEBHOOK_HOST and WEBHOOK_HOST.startswith("https://"):
    WEBHOOK_HOST = WEBHOOK_HOST[8:]  # Remove https:// prefix if present
elif WEBHOOK_HOST and WEBHOOK_HOST.startswith("http://"):
    WEBHOOK_HOST = WEBHOOK_HOST[7:]  # Remove http:// prefix if present

WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", f"/webhook/{BOT_TOKEN}")
# SSL certificate handling
WEBHOOK_SSL_CERT = os.getenv("WEBHOOK_SSL_CERT")  # Optional in production as Render handles SSL
WEBAPP_HOST = os.getenv("WEBAPP_HOST", "0.0.0.0")
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", "8000"))

# Admin settings
ADMIN_IDS: List[int] = [
    int(admin_id) for admin_id in 
    os.getenv("ADMIN_IDS", "").split(",") 
    if admin_id.strip()
]

# Database settings
DB_DIR = os.getenv("DB_DIR", "data")  # Directory for database files
DB_FILE = os.path.join(DB_DIR, os.getenv("DB_FILE", "morkovka_bot.db"))
DB_BACKUP_DIR = os.getenv("DB_BACKUP_DIR", os.path.join(DB_DIR, "backups"))
DB_BACKUP_KEEP_DAYS = int(os.getenv("DB_BACKUP_KEEP_DAYS", "30"))

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_KEEP_DAYS = int(os.getenv("LOG_KEEP_DAYS", "30"))

# Test settings
DEFAULT_TEST_PASSING_SCORE = int(os.getenv("DEFAULT_TEST_PASSING_SCORE", "70"))
DEFAULT_TEST_TIME_LIMIT = int(os.getenv("DEFAULT_TEST_TIME_LIMIT", "0"))  # 0 means no time limit

# Product settings
MAX_PRODUCT_IMAGES = int(os.getenv("MAX_PRODUCT_IMAGES", "5"))
MAX_CATEGORY_IMAGES = int(os.getenv("MAX_CATEGORY_IMAGES", "1"))

# Message settings
MAX_MESSAGE_LENGTH = 4096  # Telegram's limit
MAX_CAPTION_LENGTH = 1024  # Telegram's limit for media captions

# Rate limiting
RATE_LIMIT_MESSAGES = int(os.getenv("RATE_LIMIT_MESSAGES", "20"))  # messages per minute
RATE_LIMIT_CALLBACKS = int(os.getenv("RATE_LIMIT_CALLBACKS", "30"))  # callbacks per minute

# Cache settings
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes in seconds
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "1000"))  # maximum number of cached items

# Security settings
ALLOWED_UPDATES = [
    "message",
    "edited_message",
    "channel_post",
    "edited_channel_post",
    "inline_query",
    "chosen_inline_result",
    "callback_query",
    "shipping_query",
    "pre_checkout_query",
    "poll",
    "poll_answer",
    "my_chat_member",
    "chat_member",
    "chat_join_request"
]

# Feature flags
ENABLE_STATISTICS = os.getenv("ENABLE_STATISTICS", "true").lower() == "true"
ENABLE_USER_ACTIVITY_TRACKING = os.getenv("ENABLE_USER_ACTIVITY_TRACKING", "true").lower() == "true"
ENABLE_ADMIN_PANEL = os.getenv("ENABLE_ADMIN_PANEL", "true").lower() == "true"
ENABLE_TEST_SYSTEM = os.getenv("ENABLE_TEST_SYSTEM", "true").lower() == "true"
ENABLE_PRODUCT_CATALOG = os.getenv("ENABLE_PRODUCT_CATALOG", "true").lower() == "true"

def validate_config() -> None:
    """Validate configuration settings"""
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is required")
    
    if IS_PRODUCTION:
        if not WEBHOOK_HOST:
            raise ValueError(
                "WEBHOOK_HOST or RENDER_EXTERNAL_URL is required in production mode. "
                "Please ensure the environment variable is set in your Render dashboard."
            )
    
    if not ADMIN_IDS:
        raise ValueError("At least one ADMIN_ID is required")
    
    # Create necessary directories
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(DB_BACKUP_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Ensure database file directory exists
    db_dir = os.path.dirname(DB_FILE)
    if db_dir:  # Only create if there's a directory path
        os.makedirs(db_dir, exist_ok=True)

# Validate configuration on import
validate_config()
