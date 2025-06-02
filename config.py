"""Configuration settings for the bot"""

import os
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv
import logging
import shutil

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR: Path = Path(__file__).parent

# Bot settings
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

# Environment settings
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# Directory settings
DB_DIR: Path = Path(os.getenv("DB_DIR", "data"))
DB_FILE: Path = DB_DIR / os.getenv("DB_FILE", "morkovka_bot.db")
DB_BACKUP_DIR: Path = Path(os.getenv("DB_BACKUP_DIR", "backups"))
DB_MIGRATIONS_DIR: Path = Path(os.getenv("DB_MIGRATIONS_DIR", "migrations"))
LOG_DIR: Path = Path(os.getenv("LOG_DIR", "logs"))
METRICS_DIR: Path = Path(os.getenv("METRICS_DIR", "metrics"))
MEDIA_DIR: Path = Path("media")
PRODUCT_IMAGE_DIR: Path = MEDIA_DIR / "products"
CATEGORY_IMAGE_DIR: Path = MEDIA_DIR / "categories"
TEST_IMAGE_DIR: Path = MEDIA_DIR / "tests"
USER_IMAGE_DIR: Path = MEDIA_DIR / "users"
TEMP_DIR: Path = MEDIA_DIR / "temp"

# Create all necessary directories
REQUIRED_DIRECTORIES = [
    LOG_DIR,
    METRICS_DIR,
    DB_BACKUP_DIR,
    DB_DIR,
    MEDIA_DIR,
    PRODUCT_IMAGE_DIR,
    CATEGORY_IMAGE_DIR,
    TEST_IMAGE_DIR,
    USER_IMAGE_DIR,
    TEMP_DIR,
    DB_MIGRATIONS_DIR
]

for directory in REQUIRED_DIRECTORIES:
    directory.mkdir(parents=True, exist_ok=True)

# Webhook settings (for production)
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST") or os.getenv("RENDER_EXTERNAL_URL")  # Try both variables
if WEBHOOK_HOST and WEBHOOK_HOST.startswith("https://"):
    WEBHOOK_HOST = WEBHOOK_HOST[8:]  # Remove https:// prefix if present
elif WEBHOOK_HOST and WEBHOOK_HOST.startswith("http://"):
    WEBHOOK_HOST = WEBHOOK_HOST[7:]  # Remove http:// prefix if present

WEBHOOK_PATH: str = os.getenv("WEBHOOK_PATH", f"/webhook/{BOT_TOKEN}")
WEBHOOK_URL: Optional[str] = f"https://{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else None  # Construct full webhook URL

# SSL certificate handling
WEBHOOK_SSL_CERT = os.getenv("WEBHOOK_SSL_CERT")  # Optional in production as Render handles SSL
WEBHOOK_SSL_PRIV = os.getenv("WEBHOOK_SSL_PRIV")  # Optional in production as Render handles SSL
WEBAPP_HOST: str = os.getenv("WEBAPP_HOST", "0.0.0.0")
# Use Render's PORT environment variable, fallback to 8000 for development, and handle empty strings robustly
WEBAPP_PORT: int = int(os.getenv("PORT") or os.getenv("WEBAPP_PORT") or "8000")

# Admin settings
ADMIN_IDS: List[int] = [
    int(admin_id) for admin_id in 
    os.getenv("ADMIN_IDS", "").split(",") 
    if admin_id.strip()
]

# Database settings
DB_BACKUP_KEEP_DAYS = int(os.getenv("DB_BACKUP_KEEP_DAYS", "30"))
DB_BACKUP_COMPRESS = os.getenv("DB_BACKUP_COMPRESS", "true").lower() == "true"
DB_BACKUP_SCHEDULE = os.getenv("DB_BACKUP_SCHEDULE", "0 0 * * *")  # Daily at midnight
DB_BACKUP_MAX_SIZE = int(os.getenv("DB_BACKUP_MAX_SIZE", "100"))  # Maximum backup size in MB
DB_BACKUP_MIN_FREE_SPACE = int(os.getenv("DB_BACKUP_MIN_FREE_SPACE", "500"))  # Minimum free space in MB
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))  # Maximum number of concurrent database connections
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))  # Connection timeout in seconds
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # Connection recycle time in seconds
DB_POOL_CLEANUP_INTERVAL = int(os.getenv("DB_POOL_CLEANUP_INTERVAL", "300"))  # Cleanup interval in seconds

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_KEEP_DAYS = int(os.getenv("LOG_KEEP_DAYS", "30"))

# Test settings
DEFAULT_TEST_PASSING_SCORE: int = int(os.getenv("DEFAULT_TEST_PASSING_SCORE", "70"))
DEFAULT_TEST_TIME_LIMIT: int = int(os.getenv("DEFAULT_TEST_TIME_LIMIT", "0"))  # 0 means no time limit
MIN_QUESTIONS_PER_TEST: int = 3  # Minimum number of questions in a test
MAX_QUESTIONS_PER_TEST: int = 20  # Maximum number of questions in a test
MIN_OPTIONS_PER_QUESTION: int = 2  # Minimum number of options per question
MAX_OPTIONS_PER_QUESTION: int = 6  # Maximum number of options per question

# Product settings
MAX_PRODUCT_IMAGES: int = int(os.getenv("MAX_PRODUCT_IMAGES", "5"))
MAX_CATEGORY_IMAGES: int = int(os.getenv("MAX_CATEGORY_IMAGES", "1"))

# Message settings
MAX_MESSAGE_LENGTH = 4096  # Telegram's limit
MAX_CAPTION_LENGTH = 1024  # Telegram's limit for media captions

# Rate limiting
RATE_LIMIT_MESSAGES = int(os.getenv("RATE_LIMIT_MESSAGES", "20"))  # messages per window
RATE_LIMIT_CALLBACKS = int(os.getenv("RATE_LIMIT_CALLBACKS", "30"))  # callbacks per window
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # window size in seconds
RATE_LIMIT_BYPASS_ADMINS = os.getenv("RATE_LIMIT_BYPASS_ADMINS", "true").lower() == "true"

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
ENABLE_ADMIN_PANEL: bool = bool(ADMIN_IDS)
ENABLE_TEST_SYSTEM = os.getenv("ENABLE_TEST_SYSTEM", "true").lower() == "true"
ENABLE_PRODUCT_CATALOG = os.getenv("ENABLE_PRODUCT_CATALOG", "true").lower() == "true"

# Session settings
SESSION_TIMEOUT_MINUTES: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))

# Search settings
MIN_SEARCH_LENGTH: int = 3  # Minimum length of search query
MAX_SEARCH_RESULTS: int = 10  # Maximum number of search results to show

# Monitoring settings
METRICS_RETENTION_DAYS = int(os.getenv("METRICS_RETENTION_DAYS", "7"))
MAX_MEMORY_USAGE_MB = int(os.getenv("MAX_MEMORY_USAGE_MB", "512"))  # 512MB limit for Render free tier
MAX_CPU_USAGE_PERCENT = int(os.getenv("MAX_CPU_USAGE_PERCENT", "80"))
ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"
METRICS_COLLECTION_INTERVAL = int(os.getenv("METRICS_COLLECTION_INTERVAL", "60"))  # seconds
METRICS_CLEANUP_INTERVAL = int(os.getenv("METRICS_CLEANUP_INTERVAL", "3600"))  # seconds

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
    
    if not all(isinstance(id, int) for id in ADMIN_IDS):
        raise ValueError("ADMIN_IDS must be a comma-separated list of integers")
    
    if SESSION_TIMEOUT_MINUTES < 1:
        raise ValueError("SESSION_TIMEOUT_MINUTES must be at least 1")
    
    if DEFAULT_TEST_PASSING_SCORE < 0 or DEFAULT_TEST_PASSING_SCORE > 100:
        raise ValueError("DEFAULT_TEST_PASSING_SCORE must be between 0 and 100")
    
    if DEFAULT_TEST_TIME_LIMIT < 0:
        raise ValueError("DEFAULT_TEST_TIME_LIMIT must be at least 0 (0 means no time limit)")
    
    if MIN_QUESTIONS_PER_TEST < 1:
        raise ValueError("MIN_QUESTIONS_PER_TEST must be at least 1")
    
    if MAX_QUESTIONS_PER_TEST < MIN_QUESTIONS_PER_TEST:
        raise ValueError("MAX_QUESTIONS_PER_TEST must be greater than MIN_QUESTIONS_PER_TEST")
    
    if MIN_OPTIONS_PER_QUESTION < 2:
        raise ValueError("MIN_OPTIONS_PER_QUESTION must be at least 2")
    
    if MAX_OPTIONS_PER_QUESTION < MIN_OPTIONS_PER_QUESTION:
        raise ValueError("MAX_OPTIONS_PER_QUESTION must be greater than MIN_OPTIONS_PER_QUESTION")
    
    if MIN_SEARCH_LENGTH < 1:
        raise ValueError("MIN_SEARCH_LENGTH must be at least 1")
    
    if MAX_SEARCH_RESULTS < 1:
        raise ValueError("MAX_SEARCH_RESULTS must be at least 1")
    
    # Validate database pool settings
    if DB_POOL_SIZE < 1:
        raise ValueError("DB_POOL_SIZE must be at least 1")
    if DB_POOL_TIMEOUT < 1:
        raise ValueError("DB_POOL_TIMEOUT must be at least 1 second")
    if DB_POOL_RECYCLE < 60:
        raise ValueError("DB_POOL_RECYCLE must be at least 60 seconds")
    if DB_POOL_CLEANUP_INTERVAL < 60:
        raise ValueError("DB_POOL_CLEANUP_INTERVAL must be at least 60 seconds")
    
    # Validate monitoring settings
    if METRICS_RETENTION_DAYS < 1:
        raise ValueError("METRICS_RETENTION_DAYS must be at least 1")
    if MAX_MEMORY_USAGE_MB < 100:
        raise ValueError("MAX_MEMORY_USAGE_MB must be at least 100MB")
    if MAX_CPU_USAGE_PERCENT < 1 or MAX_CPU_USAGE_PERCENT > 100:
        raise ValueError("MAX_CPU_USAGE_PERCENT must be between 1 and 100")
    if METRICS_COLLECTION_INTERVAL < 10:
        raise ValueError("METRICS_COLLECTION_INTERVAL must be at least 10 seconds")
    if METRICS_CLEANUP_INTERVAL < 300:
        raise ValueError("METRICS_CLEANUP_INTERVAL must be at least 300 seconds")
    
    # Validate rate limiting settings
    if RATE_LIMIT_MESSAGES < 1:
        raise ValueError("RATE_LIMIT_MESSAGES must be at least 1")
    if RATE_LIMIT_CALLBACKS < 1:
        raise ValueError("RATE_LIMIT_CALLBACKS must be at least 1")
    if RATE_LIMIT_WINDOW < 1:
        raise ValueError("RATE_LIMIT_WINDOW must be at least 1 second")
    
    # Validate backup settings
    if DB_BACKUP_KEEP_DAYS < 1:
        raise ValueError("DB_BACKUP_KEEP_DAYS must be at least 1")
    if DB_BACKUP_MAX_SIZE < 10:
        raise ValueError("DB_BACKUP_MAX_SIZE must be at least 10MB")
    if DB_BACKUP_MIN_FREE_SPACE < 100:
        raise ValueError("DB_BACKUP_MIN_FREE_SPACE must be at least 100MB")
    
    # Check free space
    if DB_BACKUP_DIR.exists():
        free_space_mb = shutil.disk_usage(DB_BACKUP_DIR).free / (1024 * 1024)
        if free_space_mb < DB_BACKUP_MIN_FREE_SPACE:
            raise ValueError(
                f"Insufficient free space for backups. "
                f"Required: {DB_BACKUP_MIN_FREE_SPACE}MB, "
                f"Available: {free_space_mb:.1f}MB"
            )

# Validate configuration on import
validate_config()
