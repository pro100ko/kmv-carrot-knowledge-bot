"""Development configuration."""

from typing import Dict, Any
from .base import BaseConfig, Field, validator

class DevelopmentConfig(BaseConfig):
    """Development configuration with relaxed settings."""
    
    # Override defaults for development
    ENVIRONMENT: str = "development"
    
    # Database settings
    DB_FILE: str = Field("data/dev.db", description="Development database file path")
    DB_POOL_SIZE: int = Field(default=3, ge=1, description="Smaller pool size for development")
    
    # Logging settings
    LOG_LEVEL: str = Field(default="DEBUG", description="Debug logging level")
    LOG_FILE: str = Field("logs/dev.log", description="Development log file path")
    
    # Feature flags for development
    ENABLE_POLLING: bool = Field(default=True, description="Enable polling mode in development")
    ENABLE_WEBHOOK: bool = Field(default=False, description="Disable webhook mode in development")
    ENABLE_METRICS: bool = Field(default=False, description="Disable metrics in development")
    
    # Rate limiting for development
    RATE_LIMIT_MESSAGES: int = Field(default=100, ge=1, description="Relaxed message rate limit")
    RATE_LIMIT_CALLBACKS: int = Field(default=150, ge=1, description="Relaxed callback rate limit")
    
    # Development-specific settings
    DEBUG_MODE: bool = Field(default=True, description="Enable debug mode")
    AUTO_RELOAD: bool = Field(default=True, description="Enable auto-reload for handlers")
    TEST_MODE: bool = Field(default=False, description="Enable test mode for specific functionalities")
    
    @validator("ENABLE_POLLING", always=True)
    def validate_polling_and_webhook(cls, v: bool, values: Dict[str, Any]) -> bool:
        """Ensure webhook and polling are not enabled simultaneously."""
        if v and values.get("ENABLE_WEBHOOK"):
            raise ValueError("Cannot enable both polling and webhook modes simultaneously.")
        return v
    
    @validator("TEST_MODE")
    def validate_test_mode(cls, v: bool, values: Dict[str, Any]) -> bool:
        """Test mode requires debug mode to be enabled."""
        if v and not values.get("DEBUG_MODE"):
            raise ValueError("Test mode requires debug mode to be enabled.")
        return v
    
    class Config:
        """Pydantic config."""
        env_prefix = "DEV_"  # Use DEV_ prefix for development settings 