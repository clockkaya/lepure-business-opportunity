"""
测试项目结构

验证所有模块可以正确导入
"""
import pytest


def test_config_imports():
    """测试配置层导入"""
    from app.config.settings import Settings
    assert Settings is not None


def test_models_imports():
    """测试模型层导入"""
    from app.models.article import Article
    from app.models.project import ExtractedProject
    assert Article is not None
    assert ExtractedProject is not None


def test_services_imports():
    """测试服务层导入"""
    from app.services.rss_service import RSSService
    from app.services.llm_service import LLMService
    from app.services.notification_service import NotificationService
    assert RSSService is not None
    assert LLMService is not None
    assert NotificationService is not None


def test_utils_imports():
    """测试工具层导入"""
    from app.utils.logger import setup_logging, get_logger
    from app.utils.html_parser import clean_html
    from app.utils.db_utils import create_db_engine, check_db_health
    assert setup_logging is not None
    assert get_logger is not None
    assert clean_html is not None
    assert create_db_engine is not None
    assert check_db_health is not None


def test_html_parser():
    """测试 HTML 解析器"""
    from app.utils.html_parser import clean_html

    html = "<div><p>测试内容</p><script>alert('test')</script></div>"
    result = clean_html(html)

    assert "测试内容" in result
    assert "script" not in result
    assert "alert" not in result


def test_rss_service_initialization():
    """测试 RSS 服务初始化"""
    from app.services.rss_service import RSSService

    service = RSSService("http://localhost:4000", "test_auth")
    assert service.wewe_rss_url == "http://localhost:4000"
    assert service.auth_code == "test_auth"


def test_llm_service_initialization():
    """测试 LLM 服务初始化"""
    from app.services.llm_service import LLMService

    service = LLMService("http://localhost:11434", "test_model")
    assert service.ollama_base_url == "http://localhost:11434"
    assert service.model_name == "test_model"


def test_notification_service_initialization():
    """测试通知服务初始化"""
    from app.services.notification_service import NotificationService

    service = NotificationService("https://qyapi.weixin.qq.com/test")
    assert service.webhook_url == "https://qyapi.weixin.qq.com/test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
