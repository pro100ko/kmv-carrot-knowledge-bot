"""Tests for configuration files."""

import os
import pytest
from pathlib import Path
import importlib.util
import sys

def load_module(module_name: str, file_path: str):
    """Load a module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

@pytest.fixture
def config():
    """Load the main config module."""
    return load_module('config', 'config.py')

@pytest.fixture
def bot_config():
    """Load the bot config module."""
    return load_module('bot_config', 'bot_config.py')

def test_config_files_exist():
    """Test that both config files exist."""
    assert Path('config.py').exists(), "config.py does not exist"
    assert Path('bot_config.py').exists(), "bot_config.py does not exist"

def test_bot_token_present(config, bot_config):
    """Test that BOT_TOKEN is present in both configs."""
    assert hasattr(config, 'BOT_TOKEN'), "BOT_TOKEN not found in config.py"
    assert hasattr(bot_config, 'BOT_TOKEN'), "BOT_TOKEN not found in bot_config.py"

def test_webhook_settings(config, bot_config):
    """Test webhook settings in both configs."""
    # Check config.py
    assert hasattr(config, 'WEBHOOK_HOST'), "WEBHOOK_HOST not found in config.py"
    assert hasattr(config, 'WEBHOOK_PATH'), "WEBHOOK_PATH not found in config.py"
    assert hasattr(config, 'WEBHOOK_SECRET'), "WEBHOOK_SECRET not found in config.py"
    
    # Check bot_config.py
    assert hasattr(bot_config, 'WEBHOOK_HOST'), "WEBHOOK_HOST not found in bot_config.py"
    assert hasattr(bot_config, 'WEBHOOK_PATH'), "WEBHOOK_PATH not found in bot_config.py"
    assert hasattr(bot_config, 'WEBHOOK_SECRET'), "WEBHOOK_SECRET not found in bot_config.py"

def test_database_settings(config, bot_config):
    """Test database settings in both configs."""
    # Check config.py
    assert hasattr(config, 'DB_FILE'), "DB_FILE not found in config.py"
    assert hasattr(config, 'DB_POOL_SIZE'), "DB_POOL_SIZE not found in config.py"
    
    # Check bot_config.py
    assert hasattr(bot_config, 'DB_FILE'), "DB_FILE not found in bot_config.py"
    assert hasattr(bot_config, 'DB_POOL_SIZE'), "DB_POOL_SIZE not found in bot_config.py"

def test_admin_settings(config, bot_config):
    """Test admin settings in both configs."""
    # Check config.py
    assert hasattr(config, 'ADMIN_IDS'), "ADMIN_IDS not found in config.py"
    
    # Check bot_config.py
    assert hasattr(bot_config, 'ADMIN_IDS'), "ADMIN_IDS not found in bot_config.py"

def test_config_differences(config, bot_config):
    """Test that configs have different purposes."""
    # config.py should have more settings
    config_attrs = set(dir(config))
    bot_config_attrs = set(dir(bot_config))
    
    # config.py should have additional settings not in bot_config.py
    assert len(config_attrs) > len(bot_config_attrs), "config.py should have more settings than bot_config.py"
    
    # Check for specific advanced settings in config.py
    advanced_settings = {
        'DB_POOL_TIMEOUT',
        'DB_POOL_RECYCLE',
        'DB_POOL_CLEANUP_INTERVAL',
        'METRICS_RETENTION_DAYS',
        'MAX_MEMORY_USAGE_MB',
        'MAX_CPU_USAGE_PERCENT',
        'METRICS_COLLECTION_INTERVAL',
        'METRICS_CLEANUP_INTERVAL',
        'BACKUP_ENABLED',
        'BACKUP_INTERVAL',
        'MAX_BACKUPS'
    }
    
    for setting in advanced_settings:
        assert hasattr(config, setting), f"{setting} not found in config.py"
        assert not hasattr(bot_config, setting), f"{setting} should not be in bot_config.py"

def test_config_validation(config):
    """Test that config.py has validation."""
    assert hasattr(config, 'validate_config'), "validate_config function not found in config.py"
    assert callable(config.validate_config), "validate_config is not callable" 