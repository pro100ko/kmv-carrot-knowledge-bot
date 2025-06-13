"""Configuration loader module."""

import os
from typing import Dict, Any, Optional
import importlib.util
import sys
from pathlib import Path

def load_config() -> Dict[str, Any]:
    """
    Load configuration based on BOT_CONFIG_TYPE environment variable.
    
    Returns:
        Dict[str, Any]: Configuration dictionary
        
    Raises:
        ValueError: If BOT_CONFIG_TYPE is invalid or config files are missing
    """
    config_type = os.getenv('BOT_CONFIG_TYPE', 'simple').lower()
    
    if config_type not in ('simple', 'full'):
        raise ValueError(f"Invalid BOT_CONFIG_TYPE: {config_type}. Must be 'simple' or 'full'")
    
    config_file = 'bot_config.py' if config_type == 'simple' else 'config.py'
    
    if not Path(config_file).exists():
        raise ValueError(f"Configuration file {config_file} not found")
    
    # Load the module
    spec = importlib.util.spec_from_file_location('config', config_file)
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not load {config_file}")
    
    module = importlib.util.module_from_spec(spec)
    sys.modules['config'] = module
    spec.loader.exec_module(module)
    
    # Convert module to dict
    config = {
        key: value for key, value in module.__dict__.items()
        if not key.startswith('_') and not callable(value)
    }
    
    # Validate required settings
    required_settings = {
        'BOT_TOKEN',
        'WEBHOOK_HOST',
        'WEBHOOK_PATH',
        'WEBHOOK_SECRET',
        'DB_FILE',
        'DB_POOL_SIZE',
        'ADMIN_IDS'
    }
    
    missing_settings = required_settings - set(config.keys())
    if missing_settings:
        raise ValueError(f"Missing required settings in {config_file}: {missing_settings}")
    
    return config

def get_config() -> Dict[str, Any]:
    """
    Get the current configuration.
    
    Returns:
        Dict[str, Any]: Current configuration dictionary
    """
    if not hasattr(get_config, '_config'):
        get_config._config = load_config()
    return get_config._config

def reload_config() -> Dict[str, Any]:
    """
    Reload the configuration.
    
    Returns:
        Dict[str, Any]: Reloaded configuration dictionary
    """
    if hasattr(get_config, '_config'):
        delattr(get_config, '_config')
    return get_config() 