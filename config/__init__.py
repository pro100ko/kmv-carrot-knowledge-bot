"""Configuration package."""

import os
from typing import Type, Union
from functools import lru_cache
from .base import BaseConfig
from .production import ProductionConfig
from .development import DevelopmentConfig

def get_config_class() -> Type[BaseConfig]:
    """Get the appropriate config class based on environment."""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionConfig
    elif env == "development":
        return DevelopmentConfig
    else:
        raise ValueError(f"Unknown environment: {env}")

@lru_cache()
def get_config() -> Union[ProductionConfig, DevelopmentConfig]:
    """Get cached configuration instance."""
    config_class = get_config_class()
    return config_class()

def reload_config() -> Union[ProductionConfig, DevelopmentConfig]:
    """Reload configuration."""
    get_config.cache_clear()
    return get_config()

# Export commonly used types and classes
__all__ = [
    "BaseConfig",
    "ProductionConfig",
    "DevelopmentConfig",
    "get_config",
    "reload_config"
] 