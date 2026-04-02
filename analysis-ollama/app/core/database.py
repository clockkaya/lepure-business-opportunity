"""
数据库基础设施

引擎创建、连接池管理、Session 管理和数据库初始化
"""
import re
import time
from contextlib import contextmanager

import pymysql
from loguru import logger
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine


def create_db_engine(
    database_url: str,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_timeout: int = 30,
    pool_recycle: int = 3600,
    echo: bool = False
) -> Engine:
    """
    创建数据库引擎（使用内置 QueuePool）

    Args:
        database_url: 数据库连接 URL
        pool_size: 连接池大小，默认 5（单进程定时任务并发低）
        max_overflow: 最大溢出连接数，默认 10
        pool_timeout: 获取连接超时时间（秒）
        pool_recycle: 连接回收时间（秒），默认 1 小时防止 MySQL 8h 超时断开
        echo: 是否打印 SQL 语句
    """
    engine = create_engine(
        database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        pool_pre_ping=True,
        echo=echo,
        connect_args={
            "connect_timeout": 30,
            "charset": "utf8mb4"
        }
    )

    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_conn, connection_record):
        logger.debug("创建新数据库连接")

    @event.listens_for(engine, "checkout")
    def receive_checkout(dbapi_conn, connection_record, connection_proxy):
        logger.debug("从连接池获取连接")

    logger.info(
        f"数据库引擎已创建: pool_size={pool_size}, "
        f"max_overflow={max_overflow}, pool_timeout={pool_timeout}s"
    )

    return engine


@contextmanager
def get_session(engine: Engine):
    """
    获取数据库会话（上下文管理器）

    注意：不自动 commit，由调用方显式管理事务。
    仅在异常时自动 rollback。

    使用示例:
        with get_session(engine) as session:
            session.add(obj)
            session.commit()

    Args:
        engine: SQLModel 引擎

    Yields:
        Session: SQLModel 会话
    """
    with Session(engine) as session:
        try:
            yield session
        except Exception as e:
            session.rollback()
            logger.error(f"数据库会话异常，已回滚: {e}")
            raise


def get_pool_status(engine: Engine) -> dict:
    """
    获取连接池状态

    Args:
        engine: SQLModel 引擎

    Returns:
        dict: 连接池状态信息
    """
    pool = engine.pool
    return {
        'pool_size': pool.size(),
        'checked_in': pool.checkedin(),
        'checked_out': pool.checkedout(),
        'overflow': pool.overflow()
    }


def log_pool_status(engine: Engine):
    """
    记录连接池状态到日志

    Args:
        engine: SQLModel 引擎
    """
    status = get_pool_status(engine)
    logger.info(
        f"连接池状态: pool_size={status['pool_size']}, "
        f"checked_in={status['checked_in']}, checked_out={status['checked_out']}, "
        f"overflow={status['overflow']}"
    )


def check_db_health(engine: Engine) -> bool:
    """
    检查数据库连接健康状态

    Args:
        engine: SQLModel 引擎

    Returns:
        bool: 健康返回 True，否则返回 False
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.debug("数据库健康检查通过")
        return True
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        return False


def init_database_with_retry(
    database_url: str,
    db_name: str,
    db_host: str,
    db_port: int,
    db_user: str,
    db_password: str,
    max_retries: int = 3,
    retry_interval: int = 5
) -> Engine:
    """
    初始化数据库（带重试机制）

    Args:
        database_url: 数据库连接 URL
        db_name: 数据库名称
        db_host: 数据库主机
        db_port: 数据库端口
        db_user: 数据库用户
        db_password: 数据库密码
        max_retries: 最大重试次数
        retry_interval: 重试间隔（秒）

    Returns:
        Engine: 数据库引擎实例

    Raises:
        Exception: 所有重试失败后抛出异常
    """
    from sqlmodel import SQLModel

    # 验证数据库名称安全性
    if not re.match(r'^[a-zA-Z0-9_]+$', db_name):
        raise ValueError(f"非法数据库名称: {db_name}")

    logger.info("正在初始化数据库...")

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                f"尝试连接数据库 {db_host}:{db_port} "
                f"(第 {attempt}/{max_retries} 次)"
            )

            # 步骤 1: 连接 MySQL 实例并创建数据库（如果不存在）
            conn = pymysql.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                charset='utf8mb4',
                connect_timeout=30
            )
            cursor = conn.cursor()
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"数据库 '{db_name}' 已就绪")

            # 步骤 2: 创建引擎
            engine = create_db_engine(database_url)

            # 步骤 3: 创建表结构
            SQLModel.metadata.create_all(engine)
            logger.info("数据库表结构创建成功")

            # 步骤 4: 健康检查
            if not check_db_health(engine):
                raise Exception("数据库健康检查失败")

            logger.info("数据库初始化完成")
            return engine

        except Exception as e:
            logger.error(f"数据库初始化失败 (第 {attempt}/{max_retries} 次): {e}")

            if attempt < max_retries:
                logger.warning(f"{retry_interval} 秒后重试...")
                time.sleep(retry_interval)
            else:
                logger.error("=" * 80)
                logger.error("所有重试均失败，无法连接数据库")
                logger.error("=" * 80)
                logger.error("请检查:")
                logger.error("1. MySQL 服务是否运行")
                logger.error(f"2. DB_HOST ({db_host}) 和 DB_PORT ({db_port}) 是否正确")
                logger.error(f"3. DB_USER ({db_user}) 和 DB_PASSWORD 是否有效")
                logger.error(f"4. 数据库 '{db_name}' 是否可以创建/访问")
                logger.error("=" * 80)
                raise e
