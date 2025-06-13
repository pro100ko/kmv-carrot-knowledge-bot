"""Tests for configuration loader."""

import os
import pytest
from pathlib import Path
from config_loader import load_config, get_config, reload_config

@pytest.fixture
def env_simple():
    """Set environment to use simple config."""
    os.environ['BOT_CONFIG_TYPE'] = 'simple'
    yield
    del os.environ['BOT_CONFIG_TYPE']

@pytest.fixture
def env_full():
    """Set environment to use full config."""
    os.environ['BOT_CONFIG_TYPE'] = 'full'
    yield
    del os.environ['BOT_CONFIG_TYPE']

def test_load_config_simple(env_simple):
    """Test loading simple configuration."""
    config = load_config()
    assert isinstance(config, dict)
    assert 'BOT_TOKEN' in config
    assert 'WEBHOOK_HOST' in config
    assert 'WEBHOOK_PATH' in config
    assert 'WEBHOOK_SECRET' in config
    assert 'DB_FILE' in config
    assert 'DB_POOL_SIZE' in config
    assert 'ADMIN_IDS' in config

def test_load_config_full(env_full):
    """Test loading full configuration."""
    config = load_config()
    assert isinstance(config, dict)
    assert 'BOT_TOKEN' in config
    assert 'WEBHOOK_HOST' in config
    assert 'WEBHOOK_PATH' in config
    assert 'WEBHOOK_SECRET' in config
    assert 'DB_FILE' in config
    assert 'DB_POOL_SIZE' in config
    assert 'ADMIN_IDS' in config
    
    # Check for advanced settings
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
        assert setting in config, f"{setting} not found in full config"

def test_invalid_config_type():
    """Test loading with invalid config type."""
    os.environ['BOT_CONFIG_TYPE'] = 'invalid'
    with pytest.raises(ValueError, match="Invalid BOT_CONFIG_TYPE"):
        load_config()
    del os.environ['BOT_CONFIG_TYPE']

def test_missing_config_file(env_simple, tmp_path):
    """Test loading with missing config file."""
    # Temporarily rename config file
    config_file = Path('bot_config.py')
    if config_file.exists():
        backup = config_file.with_suffix('.py.bak')
        config_file.rename(backup)
        try:
            with pytest.raises(ValueError, match="Configuration file bot_config.py not found"):
                load_config()
        finally:
            backup.rename(config_file)

def test_get_config_caching(env_simple):
    """Test that get_config caches the configuration."""
    config1 = get_config()
    config2 = get_config()
    assert config1 is config2, "get_config should return cached configuration"

def test_reload_config(env_simple):
    """Test that reload_config forces a reload."""
    config1 = get_config()
    config2 = reload_config()
    assert config1 is not config2, "reload_config should return new configuration"

def test_required_settings(env_simple, tmp_path):
    """Test that all required settings are present."""
    # Create a minimal config file
    config_file = Path('bot_config.py')
    if config_file.exists():
        backup = config_file.with_suffix('.py.bak')
        config_file.rename(backup)
        try:
            with open(config_file, 'w') as f:
                f.write("""
# Minimal config
BOT_TOKEN = 'test'
WEBHOOK_HOST = 'test'
WEBHOOK_PATH = 'test'
WEBHOOK_SECRET = 'test'
DB_FILE = 'test'
DB_POOL_SIZE = 5
ADMIN_IDS = [1]
""")
            
            config = load_config()
            assert all(key in config for key in {
                'BOT_TOKEN',
                'WEBHOOK_HOST',
                'WEBHOOK_PATH',
                'WEBHOOK_SECRET',
                'DB_FILE',
                'DB_POOL_SIZE',
                'ADMIN_IDS'
            })
        finally:
            backup.rename(config_file)

def test_missing_required_settings(env_simple, tmp_path):
    """Test that missing required settings raise an error."""
    # Create an incomplete config file
    config_file = Path('bot_config.py')
    if config_file.exists():
        backup = config_file.with_suffix('.py.bak')
        config_file.rename(backup)
        try:
            with open(config_file, 'w') as f:
                f.write("""
# Incomplete config
BOT_TOKEN = 'test'
WEBHOOK_HOST = 'test'
# Missing required settings
""")
            
            with pytest.raises(ValueError, match="Missing required settings"):
                load_config()
        finally:
            backup.rename(config_file) 