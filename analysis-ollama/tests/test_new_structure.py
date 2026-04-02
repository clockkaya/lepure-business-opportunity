"""
测试项目结构

验证所有模块可以正确导入
"""
import pytest


def test_config_imports():
    """测试配置层导入"""
    from app.core.settings import Settings
    assert Settings is not None


def test_models_imports():
    """测试模型层导入"""
    from app.models.article import Article
    from app.models.project import ExtractedProject
    assert Article is not None
    assert ExtractedProject is not None


def test_services_imports():
    """测试服务层导入"""
    from app.services.rss_fetcher import RSSFetcher
    from app.services.llm_analyzer import LLMAnalyzer
    from app.services.wecom_notifier import WecomNotifier
    assert RSSFetcher is not None
    assert LLMAnalyzer is not None
    assert WecomNotifier is not None


def test_core_imports():
    """测试核心层导入"""
    from app.core.logging import setup_logging, get_logger
    from app.utils.html_cleaner import clean_html
    from app.core.database import create_db_engine, check_db_health
    assert setup_logging is not None
    assert get_logger is not None
    assert clean_html is not None
    assert create_db_engine is not None
    assert check_db_health is not None


def test_html_cleaner():
    """测试 HTML 清洗器"""
    from app.utils.html_cleaner import clean_html

    html = "<div><p>测试内容</p><script>alert('test')</script></div>"
    result = clean_html(html)

    assert "测试内容" in result
    assert "script" not in result
    assert "alert" not in result


def test_rss_fetcher_initialization():
    """测试 RSS 采集器初始化"""
    from app.services.rss_fetcher import RSSFetcher

    fetcher = RSSFetcher("http://localhost:4000", "test_auth")
    assert fetcher.wewe_rss_url == "http://localhost:4000"
    assert fetcher.auth_code == "test_auth"


def test_llm_analyzer_initialization():
    """测试 LLM 分析器初始化"""
    from app.services.llm_analyzer import LLMAnalyzer

    analyzer = LLMAnalyzer("deepseek-r1:32b")
    assert analyzer.default_model == "deepseek-r1:32b"


def test_wecom_notifier_initialization():
    """测试通知器初始化"""
    from app.services.wecom_notifier import WecomNotifier

    notifier = WecomNotifier("https://qyapi.weixin.qq.com/test")
    assert notifier.webhook_url == "https://qyapi.weixin.qq.com/test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
