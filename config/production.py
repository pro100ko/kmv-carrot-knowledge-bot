"""Production configuration."""

from typing import List, Dict, Any
from pathlib import Path
from .base import BaseConfig, Field

class ProductionConfig(BaseConfig):
    """Production configuration with strict settings."""
    
    # Override defaults for production
    ENVIRONMENT: str = "production"
    
    # Database settings
    DB_POOL_SIZE: int = Field(default=10, ge=5, description="Larger pool size for production")
    DB_POOL_TIMEOUT: int = Field(default=60, ge=30, description="Longer timeout for production")
    DB_POOL_RECYCLE: int = Field(default=1800, ge=300, description="More frequent recycle for production")
    
    # Monitoring settings
    METRICS_RETENTION_DAYS: int = Field(default=30, ge=7, description="Metrics retention in days")
    MAX_MEMORY_USAGE_MB: int = Field(default=1024, ge=512, description="Memory limit in MB")
    MAX_CPU_USAGE_PERCENT: int = Field(default=80, ge=50, le=90, description="CPU usage limit")
    
    # Backup settings
    BACKUP_ENABLED: bool = Field(default=True, description="Enable backups")
    BACKUP_INTERVAL: int = Field(default=86400, ge=3600, description="Backup interval in seconds")
    MAX_BACKUPS: int = Field(default=30, ge=7, description="Maximum number of backups")
    
    # Rate limiting
    RATE_LIMIT_MESSAGES: int = Field(default=30, ge=20, description="Stricter rate limits for production")
    RATE_LIMIT_CALLBACKS: int = Field(default=40, ge=30, description="Stricter rate limits for production")
    
    # Feature flags
    ENABLE_METRICS: bool = Field(default=True, description="Always enable metrics in production")
    ENABLE_HEALTH_CHECK: bool = Field(default=True, description="Always enable health check in production")
    ENABLE_POLLING: bool = Field(default=False, description="Polling mode is not allowed in production")
    
    class Config:
        """Pydantic config."""
        env_prefix = "PROD_"  # Use PROD_ prefix for production settings
        extra = "allow"  # Allow extra fields to support WEBHOOK_URL 