"""
Pytest configuration and shared fixtures for all tests.
"""
import os
import sys
import pytest
from sqlmodel import create_engine, SQLModel, Session

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def test_db_url():
    """
    Provide test database URL.
    Uses SQLite in-memory for fast, isolated unit/integration tests.
    Production uses MySQL — MySQL-specific behavior is verified manually
    and via the integration tests that connect to real services.
    """
    return "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine(test_db_url):
    """Create test database engine."""
    engine = create_engine(test_db_url, echo=False)
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_session(test_engine):
    """Create test database session for each test."""
    with Session(test_engine) as session:
        yield session
        session.rollback()


@pytest.fixture(scope="function")
def sample_article_data():
    """Provide sample article data for testing."""
    return {
        "title": "测试文章标题",
        "url": "https://example.com/article/123",
        "guid": "test-guid-123",
        "published_at": None,
        "status": "pending",
        "summary": None
    }


@pytest.fixture(scope="function")
def sample_project_data():
    """Provide sample extracted project data for testing."""
    return {
        "company_name": "测试公司",
        "province": "广东省",
        "city": "深圳市",
        "client_type": "企业",
        "application_scene": "智慧城市",
        "project_name": "智慧城市项目",
        "project_stage": "签约",
        "raw_json": {
            "company_name": "测试公司",
            "province": "广东省",
            "city": "深圳市"
        }
    }


@pytest.fixture(scope="function")
def mock_settings(monkeypatch):
    """Provide mock settings for testing."""
    monkeypatch.setenv("WEWE_RSS_URL", "http://localhost:4000")
    monkeypatch.setenv("AUTH_CODE", "test_auth")
    monkeypatch.setenv("DB_HOST", "127.0.0.1")
    monkeypatch.setenv("DB_PORT", "3308")
    monkeypatch.setenv("DB_USER", "test_user")
    monkeypatch.setenv("DB_PASSWORD", "test_pass")
    monkeypatch.setenv("DB_NAME", "test_db")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("MODEL_NAME", "test_model")
    monkeypatch.setenv("WECOM_WEBHOOK_URL", "https://qyapi.weixin.qq.com/test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    
    from app.config.settings import Settings
    return Settings()
