"""
健康检查模块

在启动时验证配置和外部依赖的可用性
"""
import requests
from typing import Tuple
from loguru import logger
from app.config.settings import settings


def validate_config() -> Tuple[bool, str]:
    """
    验证必需的配置
    
    Returns:
        Tuple[bool, str]: (是否有效, 错误消息)
    """
    try:
        # 所有必需字段都由 settings.py 中的 pydantic 验证
        # 如果到达这里，配置是有效的
        logger.info("配置验证通过")
        return True, ""
    except Exception as e:
        error_msg = f"配置验证失败: {e}"
        logger.error(error_msg)
        return False, error_msg


def check_database() -> Tuple[bool, str]:
    """
    检查数据库连接
    
    Returns:
        Tuple[bool, str]: (是否健康, 错误消息)
    """
    try:
        # 导入放在函数内部以避免循环依赖
        from app.utils.db_utils import create_db_engine, check_db_health
        
        # 创建临时引擎进行健康检查
        temp_engine = create_db_engine(
            database_url=settings.database_url,
            pool_size=1,
            max_overflow=0
        )
        
        if check_db_health(temp_engine):
            logger.info("数据库健康检查通过")
            temp_engine.dispose()
            return True, ""
        else:
            error_msg = "数据库健康检查失败"
            logger.error(error_msg)
            temp_engine.dispose()
            return False, error_msg
    except Exception as e:
        error_msg = f"数据库健康检查错误: {e}"
        logger.error(error_msg)
        return False, error_msg


def check_wewe_rss(optional: bool = True) -> Tuple[bool, str]:
    """
    检查 WeWe-RSS 连接性（可选）
    
    Args:
        optional: 如果为 True，失败不会导致启动失败
    
    Returns:
        Tuple[bool, str]: (是否可访问, 错误消息)
    """
    try:
        logger.info(f"正在检查 WeWe-RSS 连接性: {settings.WEWE_RSS_URL}")
        
        # 尝试访问基础 URL
        response = requests.get(settings.WEWE_RSS_URL, timeout=10)
        
        if response.status_code in [200, 400, 401, 403]:
            # 200: OK, 401/403: 服务正常但需要认证
            logger.info("WeWe-RSS 连接性检查通过")
            return True, ""
        else:
            error_msg = f"WeWe-RSS 返回意外状态码: {response.status_code}"
            if optional:
                logger.warning(error_msg + "（可选检查，继续）")
                return True, ""
            else:
                logger.error(error_msg)
                return False, error_msg
                
    except requests.exceptions.Timeout:
        error_msg = "WeWe-RSS 连接性检查超时（10 秒）"
        if optional:
            logger.warning(error_msg + "（可选检查，继续）")
            return True, ""
        else:
            logger.error(error_msg)
            return False, error_msg
    except requests.exceptions.ConnectionError as e:
        error_msg = f"WeWe-RSS 连接错误: {e}"
        if optional:
            logger.warning(error_msg + "（可选检查，继续）")
            return True, ""
        else:
            logger.error(error_msg)
            return False, error_msg
    except Exception as e:
        error_msg = f"WeWe-RSS 连接性检查错误: {e}"
        if optional:
            logger.warning(error_msg + "（可选检查，继续）")
            return True, ""
        else:
            logger.error(error_msg)
            return False, error_msg


def run_health_checks() -> bool:
    """
    在启动时运行所有健康检查
    
    Returns:
        bool: 所有检查通过返回 True，否则返回 False
    """
    logger.info("=" * 80)
    logger.info("正在运行启动健康检查")
    logger.info("=" * 80)
    
    all_passed = True
    
    # 1. 验证配置
    config_ok, config_err = validate_config()
    if not config_ok:
        logger.error(f"❌ 配置检查失败: {config_err}")
        all_passed = False
    else:
        logger.info("✓ 配置检查通过")
    
    # 2. 检查数据库
    db_ok, db_err = check_database()
    if not db_ok:
        logger.error(f"❌ 数据库检查失败: {db_err}")
        all_passed = False
    else:
        logger.info("✓ 数据库检查通过")
    
    # 3. 检查 WeWe-RSS（可选）
    wewe_ok, wewe_err = check_wewe_rss(optional=True)
    if not wewe_ok:
        logger.warning(f"⚠ WeWe-RSS 检查失败: {wewe_err}")
        # 可选检查失败不影响启动
    else:
        logger.info("✓ WeWe-RSS 检查通过")
    
    logger.info("=" * 80)
    if all_passed:
        logger.info("所有健康检查通过")
    else:
        logger.error("部分健康检查失败")
    logger.info("=" * 80)
    
    return all_passed
