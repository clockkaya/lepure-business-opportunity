"""
Tests for configuration settings validation.
"""
import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError


def _base_env(**overrides):
    env = {
        "WEWE_RSS_URL": "http://localhost:4000",
        "AUTH_CODE": "123567",
        "DB_HOST": "127.0.0.1",
        "DB_PORT": "3308",
        "DB_USER": "root",
        "DB_PASSWORD": "password",

        "MODEL_NAME": "deepseek-r1:32b",
        "WECOM_WEBHOOK_URL": "https://qyapi.weixin.qq.com/webhook",
    }
    env.update(overrides)
    return env


def test_settings_with_all_required_fields():
    """Test that Settings loads successfully when all required fields are provided."""
    with patch.dict(os.environ, _base_env(), clear=True):
        from app.core.settings import Settings
        settings = Settings()

        assert settings.WEWE_RSS_URL == "http://localhost:4000"
        assert settings.AUTH_CODE == "123567"
        assert settings.DB_HOST == "127.0.0.1"
        assert settings.DB_PORT == 3308
        assert settings.DB_USER == "root"
        assert settings.DB_PASSWORD == "password"
        assert settings.DB_NAME == "analysis_ollama"

        assert settings.MODEL_NAME == "deepseek-r1:32b"
        assert settings.WECOM_WEBHOOK_URL == "https://qyapi.weixin.qq.com/webhook"
        assert settings.LOG_LEVEL == "INFO"


def test_settings_db_name_default():
    """Test that DB_NAME has correct default value."""
    with patch.dict(os.environ, _base_env(), clear=True):
        from app.core.settings import Settings
        settings = Settings()
        assert settings.DB_NAME == "analysis_ollama"


def test_settings_log_level_default():
    """Test that LOG_LEVEL has correct default value."""
    with patch.dict(os.environ, _base_env(), clear=True):
        from app.core.settings import Settings
        settings = Settings()
        assert settings.LOG_LEVEL == "INFO"


def test_settings_log_level_validation():
    """Test that LOG_LEVEL validation works correctly."""
    with patch.dict(os.environ, _base_env(LOG_LEVEL="DEBUG"), clear=True):
        from app.core.settings import Settings
        settings = Settings()
        assert settings.LOG_LEVEL == "DEBUG"

    with patch.dict(os.environ, _base_env(LOG_LEVEL="INVALID"), clear=True):
        from app.core.settings import Settings
        with pytest.raises((ValidationError, ValueError)):
            Settings()


def test_settings_missing_required_field():
    """Test that missing required fields raise ValidationError."""
    env = _base_env()
    env.pop("WEWE_RSS_URL")
    with patch.dict(os.environ, env, clear=True):
        from app.core.settings import Settings
        with pytest.raises((ValidationError, ValueError)):
            Settings()


def test_settings_database_url_property():
    """Test that database_url property generates correct connection string."""
    with patch.dict(os.environ, _base_env(
        DB_HOST="127.0.0.1",
        DB_PORT="3308",
        DB_USER="testuser",
        DB_PASSWORD="testpass",
        DB_NAME="testdb",
    ), clear=True):
        from app.core.settings import Settings
        settings = Settings()
        expected_url = "mysql+pymysql://testuser:testpass@127.0.0.1:3308/testdb?charset=utf8mb4"
        assert settings.database_url == expected_url


def test_settings_whitespace_trimming():
    """Test that whitespace is trimmed from string fields."""
    with patch.dict(os.environ, _base_env(
        WEWE_RSS_URL="  http://localhost:4000  ",
        AUTH_CODE="  123567  ",
        DB_HOST="  127.0.0.1  ",
        DB_USER="  root  ",
        DB_PASSWORD="  password  ",

        MODEL_NAME="  model  ",
        WECOM_WEBHOOK_URL="  https://webhook.url  ",
    ), clear=True):
        from app.core.settings import Settings
        settings = Settings()

        assert settings.WEWE_RSS_URL == "http://localhost:4000"
        assert settings.AUTH_CODE == "123567"
        assert settings.DB_HOST == "127.0.0.1"
        assert settings.DB_USER == "root"
        assert settings.DB_PASSWORD == "password"

        assert settings.MODEL_NAME == "model"
        assert settings.WECOM_WEBHOOK_URL == "https://webhook.url"
