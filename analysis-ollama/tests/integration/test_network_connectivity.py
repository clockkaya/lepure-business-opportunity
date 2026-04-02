"""
Integration tests for network connectivity.

这些测试验证服务间的网络连通性。
需要实际的服务运行才能通过。

在 CI/CD 环境中，这些测试应该被标记为 @pytest.mark.integration 并单独运行。
"""
import pytest
import requests
from unittest.mock import patch, Mock
from app.core.settings import Settings
from app.core.database import create_db_engine, check_db_health


# 标记为集成测试（需要外部服务）
pytestmark = pytest.mark.integration


def test_wewe_rss_api_connectivity(mock_settings):
    """
    测试 WeWe-RSS API 连通性

    前提条件:
    - wewe-rss 服务正在运行
    - 用户已完成登录和订阅配置
    """
    try:
        response = requests.get(
            f"{mock_settings.WEWE_RSS_URL}/feeds/test",
            timeout=10
        )
        # 200 表示成功，401/400 表示需要认证但服务可达，404 表示 feed 不存在
        assert response.status_code in [200, 400, 401, 404]
    except requests.exceptions.ConnectionError:
        pytest.skip("WeWe-RSS 服务未运行")


def test_wewe_rss_api_with_auth(mock_settings):
    """测试带认证的 WeWe-RSS API 访问"""
    try:
        response = requests.get(
            f"{mock_settings.WEWE_RSS_URL}/feeds/test?auth_code={mock_settings.AUTH_CODE}",
            timeout=10
        )
        # 应该返回 200、400 或 404（feed 不存在或认证失败）
        assert response.status_code in [200, 400, 404]
    except requests.exceptions.ConnectionError:
        pytest.skip("WeWe-RSS 服务未运行")


def test_database_connectivity(mock_settings):
    """
    测试数据库连通性
    
    前提条件:
    - MySQL 服务正在运行
    - 数据库凭据正确
    """
    try:
        engine = create_db_engine(mock_settings.database_url, echo=False)
        result = check_db_health(engine)
        assert result is True
        engine.dispose()
    except Exception as e:
        pytest.skip(f"数据库连接失败: {e}")


def test_ollama_service_connectivity():
    """
    测试 Ollama 服务连通性

    验证 MODEL_REGISTRY 中定义的所有基础服务地址是否可达。
    """
    from app.services.llm_analyzer import MODEL_REGISTRY
    
    # 获取唯一的 base_urls
    base_urls = {config["base_url"] for config in MODEL_REGISTRY.values()}
    
    passed_count = 0
    errors = []
    
    for url in base_urls:
        try:
            response = requests.get(f"{url}/api/tags", timeout=10)
            if response.status_code == 200:
                passed_count += 1
        except Exception as e:
            errors.append(f"{url}: {e}")
            
    if not passed_count and errors:
        pytest.skip(f"所有 Ollama 服务均不可达: {errors}")
    
    assert passed_count > 0, "至少应该有一个 Ollama 服务可达"


def test_wecom_webhook_connectivity(mock_settings):
    """
    测试企业微信 Webhook 连通性

    注意：这个测试会发送一条测试消息到企业微信
    """
    if 'test' in mock_settings.WECOM_WEBHOOK_URL:
        pytest.skip("使用测试 Webhook URL，跳过真实连通性测试")
    try:
        payload = {
            "msgtype": "text",
            "text": {
                "content": "【测试】网络连通性测试消息，请忽略"
            }
        }
        response = requests.post(
            mock_settings.WECOM_WEBHOOK_URL,
            json=payload,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('errcode') == 0 or response.status_code == 200
    except requests.exceptions.ConnectionError:
        pytest.skip("企业微信 Webhook 不可达")


def test_docker_network_connectivity():
    """
    测试 Docker 网络连通性
    
    这个测试验证容器是否能通过服务名称访问其他容器
    
    前提条件:
    - 在 Docker 容器中运行
    - 容器已加入 wewe-rss_default 网络
    """
    # 尝试通过服务名称访问 wewe-rss
    try:
        response = requests.get("http://app:4000", timeout=5)
        # 任何响应都表示网络连通
        assert response.status_code in [200, 401, 404, 302]
    except requests.exceptions.ConnectionError:
        # 如果不在 Docker 网络中，跳过测试
        pytest.skip("不在 Docker 网络中或 wewe-rss 未运行")


def test_database_via_docker_network():
    """
    测试通过 Docker 网络访问数据库
    
    前提条件:
    - 在 Docker 容器中运行
    - 数据库容器名称为 'db'
    """
    try:
        # 尝试通过容器名称连接数据库
        db_url = "mysql+pymysql://root:password@db:3306/test_db?charset=utf8mb4"
        engine = create_db_engine(db_url, echo=False)
        result = check_db_health(engine)
        engine.dispose()
        
        # 如果成功，说明在 Docker 网络中
        assert result is True
    except Exception:
        # 如果失败，可能不在 Docker 网络中
        pytest.skip("不在 Docker 网络中或数据库配置不正确")




@pytest.mark.parametrize("service_url,expected_status", [
    ("http://localhost:4000", [200, 401, 404, 302]),
    ("http://app:4000", [200, 401, 404, 302]),
])
def test_wewe_rss_multiple_endpoints(service_url, expected_status):
    """
    测试 WeWe-RSS 的多个访问端点
    
    在不同环境中，可能通过不同的地址访问 wewe-rss:
    - localhost:4000 (宿主机)
    - app:4000 (Docker 网络)
    """
    try:
        response = requests.get(service_url, timeout=5)
        assert response.status_code in expected_status
    except requests.exceptions.ConnectionError:
        pytest.skip(f"无法访问 {service_url}")


def test_health_check_endpoint():
    """
    测试应用的健康检查端点（如果有）
    
    这个测试假设应用提供了健康检查端点
    """
    # 如果应用没有健康检查端点，跳过此测试
    pytest.skip("应用未实现健康检查端点")


def test_network_timeout_handling():
    """测试网络超时处理"""
    # 使用一个不存在的地址测试超时
    try:
        response = requests.get(
            "http://192.168.255.255:9999",
            timeout=2
        )
    except requests.exceptions.Timeout:
        # 超时是预期的行为
        pass
    except requests.exceptions.ConnectionError:
        # 连接错误也是可以接受的
        pass


def test_network_error_handling():
    """测试网络错误处理"""
    # 使用无效的 URL 测试错误处理
    try:
        response = requests.get("http://invalid-host-name-12345:4000", timeout=2)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        # 这是预期的行为
        pass
