"""
健康检查器

在启动时验证配置和外部依赖的可用性
"""
import requests

from loguru import logger
from app.core.settings import settings
from app.core.database import check_db_health


def check_wewe_rss(optional: bool = True) -> bool:
    """
    检查 WeWe-RSS 连接性

    Args:
        optional: 如果为 True，失败不会导致启动失败

    Returns:
        bool: 检查通过返回 True
    """
    try:
        logger.info(f"正在检查 WeWe-RSS 连接性: {settings.WEWE_RSS_URL}")
        response = requests.get(settings.WEWE_RSS_URL, timeout=10)

        if response.status_code in [200, 400, 401, 403]:
            logger.info("WeWe-RSS 连接性检查通过")
            return True

        error_msg = f"WeWe-RSS 返回意外状态码: {response.status_code}"
    except requests.exceptions.Timeout:
        error_msg = "WeWe-RSS 连接性检查超时（10 秒）"
    except requests.exceptions.ConnectionError as e:
        error_msg = f"WeWe-RSS 连接错误: {e}"
    except Exception as e:
        error_msg = f"WeWe-RSS 连接性检查错误: {e}"

    # 统一处理失败路径
    if optional:
        logger.warning(f"{error_msg}（可选检查，继续）")
        return True
    logger.error(error_msg)
    return False


def run_health_checks(engine) -> bool:
    """
    在启动时运行所有健康检查

    Args:
        engine: 已初始化的数据库引擎

    Returns:
        bool: 所有检查通过返回 True，否则返回 False
    """
    logger.info("=" * 80)
    logger.info("正在运行启动健康检查")
    logger.info("=" * 80)

    all_passed = True

    # 1. 数据库健康检查（直接复用 database.check_db_health）
    if check_db_health(engine):
        logger.info("✓ 数据库检查通过")
    else:
        logger.error("❌ 数据库检查失败")
        all_passed = False

    # 2. WeWe-RSS 连接性检查（可选）
    if check_wewe_rss(optional=True):
        logger.info("✓ WeWe-RSS 检查通过")
    else:
        logger.warning("⚠ WeWe-RSS 检查失败")

    logger.info("=" * 80)
    if all_passed:
        logger.info("所有健康检查通过")
    else:
        logger.error("部分健康检查失败")
    logger.info("=" * 80)

    return all_passed
