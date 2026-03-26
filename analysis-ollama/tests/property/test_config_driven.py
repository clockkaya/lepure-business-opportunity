"""
Property-based tests for configuration-driven behavior.

Feature: environment-separation-architecture
Property 1: 配置驱动的环境行为

对于任何有效的环境配置（dev 或 pre），当应用使用该配置启动时，
应用的行为（数据库连接地址、API 端点）应该与配置中指定的值一致，
而无需修改代码。
"""
import os
from unittest.mock import patch
from hypothesis import given, strategies as st, settings


def _make_env(overrides: dict) -> dict:
    """Build a complete env dict with required defaults."""
    base = {
        'ENV': 'dev',
        'DB_HOST': '127.0.0.1',
        'DB_PORT': '3308',
        'DB_USER': 'test_user',
        'DB_PASSWORD': 'test_pass',
        'DB_NAME': 'test_db',
        'WEWE_RSS_URL': 'http://localhost:4000',
        'AUTH_CODE': 'test_auth',
        'OLLAMA_BASE_URL': 'http://localhost:11434',
        'MODEL_NAME': 'test_model',
        'WECOM_WEBHOOK_URL': 'https://qyapi.weixin.qq.com/test',
        'LOG_LEVEL': 'INFO',
    }
    base.update(overrides)
    return base


@given(
    env=st.sampled_from(['dev', 'pre']),
    db_host=st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='.-_'
    )),
    db_port=st.integers(min_value=1024, max_value=65535)
)
@settings(max_examples=50)
def test_property_config_driven_behavior(env, db_host, db_port):
    """
    Feature: environment-separation-architecture, Property 1: 配置驱动的环境行为

    对于任何有效的环境配置，应用行为应与配置一致
    """
    env_vars = _make_env({'ENV': env, 'DB_HOST': db_host, 'DB_PORT': str(db_port)})
    with patch.dict(os.environ, env_vars, clear=True):
        from app.config.settings import Settings
        config = Settings()

        assert config.ENV == env
        assert config.DB_HOST == db_host.strip()
        assert config.DB_PORT == db_port
        assert db_host.strip() in config.database_url
        assert str(db_port) in config.database_url


@given(
    wewe_rss_url=st.text(min_size=10, max_size=100, alphabet=st.characters(blacklist_characters='\x00')).filter(lambda x: x.strip()),
    auth_code=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_characters='\x00')).filter(lambda x: x.strip())
)
@settings(max_examples=50)
def test_property_wewe_rss_config(wewe_rss_url, auth_code):
    """
    Feature: environment-separation-architecture, Property 1: 配置驱动的环境行为

    WeWe-RSS 配置应该从环境变量正确加载
    """
    env_vars = _make_env({'WEWE_RSS_URL': wewe_rss_url, 'AUTH_CODE': auth_code})
    with patch.dict(os.environ, env_vars, clear=True):
        from app.config.settings import Settings
        config = Settings()

        assert config.WEWE_RSS_URL == wewe_rss_url.strip()
        assert config.AUTH_CODE == auth_code.strip()


@given(
    log_level=st.sampled_from(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
)
@settings(max_examples=20)
def test_property_log_level_config(log_level):
    """
    Feature: environment-separation-architecture, Property 1: 配置驱动的环境行为

    日志级别应该从环境变量正确加载并验证
    """
    env_vars = _make_env({'LOG_LEVEL': log_level})
    with patch.dict(os.environ, env_vars, clear=True):
        from app.config.settings import Settings
        config = Settings()

        assert config.LOG_LEVEL == log_level.upper()


@given(
    db_name=st.text(min_size=1, max_size=64, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-'
    )).filter(lambda x: x.strip())
)
@settings(max_examples=50)
def test_property_database_url_generation(db_name):
    """
    Feature: environment-separation-architecture, Property 1: 配置驱动的环境行为

    数据库 URL 应该根据配置正确生成
    """
    db_user = 'test_user'
    db_password = 'test_pass'
    db_host = '127.0.0.1'
    db_port = 3308

    env_vars = _make_env({
        'DB_NAME': db_name,
        'DB_USER': db_user,
        'DB_PASSWORD': db_password,
        'DB_HOST': db_host,
        'DB_PORT': str(db_port),
    })
    with patch.dict(os.environ, env_vars, clear=True):
        from app.config.settings import Settings
        config = Settings()

        expected_url = (
            f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}"
            f"/{db_name.strip()}?charset=utf8mb4"
        )
        assert config.database_url == expected_url
        assert db_user in config.database_url
        assert db_password in config.database_url
        assert db_host in config.database_url
        assert str(db_port) in config.database_url
        assert db_name.strip() in config.database_url
