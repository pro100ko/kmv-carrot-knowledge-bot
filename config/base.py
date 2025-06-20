"""Base configuration module with type hints and validation."""

from typing import List, Optional, Dict, Any, Union
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from pathlib import Path
import os
from functools import lru_cache
from urllib.parse import urlparse

class BaseConfig(BaseSettings):
    """Base configuration class with validation."""
    
    # Bot settings
    BOT_TOKEN: str = Field(..., description="Telegram bot token")
    ENVIRONMENT: str = Field(default="development", description="Environment (development/production)")
    
    # Webhook settings
    WEBHOOK_HOST: Optional[str] = Field(None, description="Webhook host")
    WEBHOOK_PATH: str = Field(default="/webhook", description="Webhook path")
    WEBHOOK_SECRET: Optional[str] = Field(None, description="Webhook secret token")
    WEBHOOK_PORT: int = Field(default=10000, description="Webhook port")
    WEBHOOK_URL: Optional[str] = Field(None, description="Full webhook URL (optional)")
    
    # Server settings
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    
    # Admin settings
    ADMIN_IDS: Union[List[int], str] = Field(..., description="List of admin user IDs (comma-separated string or list)")
    
    # Database settings
    DB_FILE: Optional[Path] = Field(default=Path("bot.db"), description="Database file path")
    DB_POOL_SIZE: int = Field(default=5, ge=1, description="Database pool size")
    DB_POOL_TIMEOUT: int = Field(default=30, ge=1, description="Database pool timeout in seconds")
    DB_POOL_RECYCLE: int = Field(default=3600, ge=60, description="Database pool recycle time in seconds")
    DB_BACKUP_DIR: Path = Field(default=Path("backups"), description="Database backup directory")
    DB_MIGRATIONS_DIR: Path = Field(default=Path("migrations"), description="Database migrations directory")
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    LOG_FILE: Optional[str] = Field(None, description="Log file path")
    
    # Rate limiting
    RATE_LIMIT_MESSAGES: int = Field(default=20, ge=1, description="Message rate limit per window")
    RATE_LIMIT_CALLBACKS: int = Field(default=30, ge=1, description="Callback rate limit per window")
    RATE_LIMIT_WINDOW: int = Field(default=60, ge=1, description="Rate limit window in seconds")
    
    # Security
    ALLOWED_UPDATES: List[str] = Field(
        default=["message", "edited_message", "callback_query"],
        description="Allowed update types"
    )
    
    # Feature flags
    ENABLE_WEBHOOK: bool = Field(default=True, description="Enable webhook mode")
    ENABLE_POLLING: bool = Field(default=False, description="Enable polling mode")
    ENABLE_METRICS: bool = Field(default=True, description="Enable metrics collection")
    ENABLE_HEALTH_CHECK: bool = Field(default=True, description="Enable health check endpoint")
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        if v not in ("development", "production", "testing"):
            raise ValueError("ENVIRONMENT must be one of: development, production, testing")
        return v
    
    @validator("WEBHOOK_HOST", pre=True)
    def validate_webhook_host(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        """Validate and set webhook host."""
        if values.get("ENVIRONMENT") == "production":
            if not v:
                # Extract bot name from token for Render
                token = values.get("BOT_TOKEN", "")
                if token:
                    bot_name = token.split(":")[0]
                    return f"https://{bot_name}.onrender.com"
                raise ValueError("BOT_TOKEN is required to set WEBHOOK_HOST")
            return v
        return v or ""
    
    @validator("WEBHOOK_URL", pre=True)
    def validate_webhook_url(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        """Validate webhook URL."""
        if v:
            # If URL is provided, extract host
            parsed = urlparse(v)
            if parsed.scheme and parsed.netloc:
                values["WEBHOOK_HOST"] = f"{parsed.scheme}://{parsed.netloc}"
                return v
        return None
    
    @validator("ADMIN_IDS", pre=True)
    def validate_admin_ids(cls, v: Union[List[int], str]) -> List[int]:
        """Validate and convert admin IDs to list of integers."""
        if isinstance(v, str):
            try:
                # Split by comma and convert to integers
                v = [int(x.strip()) for x in v.split(",") if x.strip()]
            except ValueError:
                raise ValueError("ADMIN_IDS must be a comma-separated list of integers")
        
        if not v:
            raise ValueError("At least one ADMIN_ID is required")
        
        return v
    
    @validator("WEBHOOK_SECRET")
    def validate_webhook_secret(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        """Validate webhook secret in production."""
        if values.get("ENVIRONMENT") == "production" and not v:
            # Generate a random secret if not provided
            import secrets
            return secrets.token_urlsafe(32)
        return v
    
    @validator("DB_FILE")
    def validate_db_file(cls, v: Optional[Path], values: Dict[str, Any]) -> Path:
        """Validate database file path."""
        if v is None:
            # Use default path in production
            if values.get("ENVIRONMENT") == "production":
                return Path("/opt/render/project/src/bot.db")
            return Path("bot.db")
        v.parent.mkdir(parents=True, exist_ok=True)
        return v
    
    @validator("DB_BACKUP_DIR")
    def validate_backup_dir(cls, v: Path) -> Path:
        """Validate backup directory path."""
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    @validator("DB_MIGRATIONS_DIR")
    def validate_migrations_dir(cls, v: Path) -> Path:
        """Validate migrations directory path."""
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(valid_levels)}")
        return v.upper()
    
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.ENVIRONMENT == "production"
    
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.ENVIRONMENT == "development"
    
    def is_testing(self) -> bool:
        """Check if running in testing."""
        return self.ENVIRONMENT == "testing" 