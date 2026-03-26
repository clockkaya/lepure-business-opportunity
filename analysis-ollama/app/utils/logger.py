"""
日志工具 - 使用 Loguru

提供简洁的日志配置
"""
from loguru import logger
import sys


def setup_logging(log_level: str = "INFO", json_format: bool = False):
    """
    配置应用程序日志
    
    Args:
        log_level: 日志级别，默认为 INFO
        json_format: 是否使用 JSON 格式输出，默认为 False
    """
    # 移除默认处理器
    logger.remove()
    
    if json_format:
        # JSON 格式输出（生产环境推荐）
        logger.add(
            sys.stdout,
            level=log_level,
            serialize=True,  # 自动序列化为 JSON
            backtrace=True,  # 显示完整堆栈
            diagnose=True    # 显示变量值
        )
    else:
        # 彩色格式输出（开发环境推荐）
        logger.add(
            sys.stdout,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True,
            backtrace=True,
            diagnose=True
        )
    
    logger.info(f"日志系统已初始化，级别: {log_level}, JSON 格式: {json_format}")


def get_logger(name: str):
    """
    获取指定名称的日志记录器（兼容标准 logging 接口的测试）
    
    Args:
        name: 模块名称
    Returns:
        绑定了名称的 loguru logger
    """
    return logger.bind(name=name)


__all__ = ['logger', 'setup_logging', 'get_logger']
