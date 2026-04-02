"""
主程序入口

初始化服务并启动定时任务
"""
import sys
import time

import schedule
from loguru import logger

from app.core.logging import setup_logging
from app.core.database import init_database_with_retry, get_session, log_pool_status
from app.core.settings import settings
from app.core.health_checker import run_health_checks
from app.services.processor import ArticleProcessor
from app.services.rss_fetcher import RSSFetcher
from app.services.llm_analyzer import LLMAnalyzer
from app.services.wecom_notifier import WecomNotifier


def main():
    """主函数"""
    # 初始化日志（在 main() 内部，避免模块级副作用）
    setup_logging(
        log_level=settings.LOG_LEVEL,
        json_format=False
    )

    logger.info("=" * 80)
    logger.info("Analysis-Ollama 服务启动中")
    logger.info(f"环境: {settings.ENV}")
    logger.info(f"数据库: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    logger.info(f"WeWe-RSS: {settings.WEWE_RSS_URL}")
    logger.info(f"默认模型: {settings.MODEL_NAME}")

    # 根据配置决定调度方式
    if settings.CRON_SCHEDULE:
        logger.info("调度方式: Cron 定时任务")
        logger.info(f"执行时间: {settings.CRON_SCHEDULE}")
    else:
        logger.info("调度方式: 轮询")
        logger.info(f"轮询间隔: {settings.POLL_INTERVAL_MINUTES} 分钟")

    logger.info("=" * 80)

    # 初始化数据库引擎
    engine = init_database_with_retry(
        database_url=settings.database_url,
        db_name=settings.DB_NAME,
        db_host=settings.DB_HOST,
        db_port=settings.DB_PORT,
        db_user=settings.DB_USER,
        db_password=settings.DB_PASSWORD
    )

    # 启动时运行健康检查（复用主引擎）
    if not run_health_checks(engine):
        logger.error("健康检查失败，退出")
        sys.exit(1)

    # 初始化服务
    rss_fetcher = RSSFetcher(
        settings.WEWE_RSS_URL, settings.AUTH_CODE,
        timeout=settings.RSS_FETCH_TIMEOUT,
        batch_size=settings.RSS_FETCH_BATCH_SIZE,
    )
    llm_analyzer = LLMAnalyzer(default_model=settings.MODEL_NAME)
    wecom_notifier = WecomNotifier(settings.WECOM_WEBHOOK_URL)

    # 初始化处理器
    processor = ArticleProcessor(rss_fetcher, llm_analyzer, wecom_notifier)

    def process_routine_wrapper():
        """处理流程包装器"""
        with get_session(engine) as session:
            processor.process_routine(session)

        # 记录连接池状态
        log_pool_status(engine)

    # 启动时立即执行一次
    process_routine_wrapper()

    # 根据配置决定调度方式
    if settings.CRON_SCHEDULE:
        cron_times = settings.CRON_SCHEDULE.split(',')
        for time_str in cron_times:
            schedule.every().day.at(time_str.strip()).do(process_routine_wrapper)
            logger.info(f"已添加定时任务: 每天 {time_str.strip()}")

        logger.info("调度器已启动，使用 Cron 定时任务")
    else:
        schedule.every(settings.POLL_INTERVAL_MINUTES).minutes.do(process_routine_wrapper)
        logger.info(f"调度器已启动，每 {settings.POLL_INTERVAL_MINUTES} 分钟轮询一次")

    # 主循环
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
    finally:
        engine.dispose()
        logger.info("服务已停止")


if __name__ == "__main__":
    main()
