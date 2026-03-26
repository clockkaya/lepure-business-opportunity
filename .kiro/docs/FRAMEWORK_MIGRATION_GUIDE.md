# 框架迁移实施指南

本文档提供详细的步骤，用于将项目迁移到推荐的最佳实践框架。

---

## 阶段 1: 日志系统迁移到 Loguru

### 1.1 安装依赖

```bash
pip install loguru
```

### 1.2 更新 requirements.txt

```diff
- python-json-logger==2.0.7
+ loguru==0.7.2
```

### 1.3 简化 utils/logger.py

**新的 logger.py**:
```python
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


# 直接导出 logger，无需 get_logger() 函数
__all__ = ['logger', 'setup_logging']
```

### 1.4 更新所有模块的导入

**查找并替换**:

```bash
# 查找所有使用旧 logger 的文件
grep -r "from utils.logger import" analysis-ollama/

# 或使用 Python 脚本批量替换
```

**替换规则**:

```diff
# 旧代码
- import logging
- from utils.logger import setup_logging, get_logger
- logger = get_logger(__name__)
- logger = logging.getLogger(__name__)

# 新代码
+ from loguru import logger
```

**受影响的文件**:
- `main.py`
- `core/processor.py`
- `core/health_check.py`
- `services/rss_service.py`
- `services/llm_service.py`
- `services/notification_service.py`
- `repositories/article_repository.py`
- `utils/db_utils.py`

### 1.5 更新 main.py

```python
from loguru import logger
from utils.logger import setup_logging
from config.settings import settings

# 配置日志
setup_logging(
    log_level=settings.LOG_LEVEL,
    json_format=(settings.ENVIRONMENT == "pre")  # 生产环境使用 JSON
)

logger.info(f"应用启动，环境: {settings.ENVIRONMENT}")
```

### 1.6 Loguru 高级特性

**日志轮转**:
```python
logger.add(
    "logs/app_{time:YYYY-MM-DD}.log",
    rotation="00:00",  # 每天午夜轮转
    retention="30 days",  # 保留 30 天
    compression="zip"  # 压缩旧日志
)
```

**异步日志**:
```python
logger.add(
    sys.stdout,
    level="INFO",
    enqueue=True  # 异步写入，提高性能
)
```

**上下文绑定**:
```python
# 绑定上下文信息
logger_with_context = logger.bind(feed_id="feed_123", user="admin")
logger_with_context.info("处理文章")
# 输出: ... | feed_id=feed_123 user=admin | 处理文章
```

---

## 阶段 2: 简化数据库连接池

### 2.1 简化 utils/db_utils.py

**新的 db_utils.py**:
```python
"""
数据库工具模块

使用 SQLAlchemy 内置连接池
"""
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from contextlib import contextmanager
from loguru import logger
import time
import pymysql


def create_db_engine(
    database_url: str,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_timeout: int = 30,
    pool_recycle: int = 3600,
    echo: bool = False
) -> Engine:
    """
    创建数据库引擎（使用内置 QueuePool）
    
    Args:
        database_url: 数据库连接 URL
        pool_size: 连接池大小
        max_overflow: 最大溢出连接数
        pool_timeout: 获取连接超时时间（秒）
        pool_recycle: 连接回收时间（秒）
        echo: 是否打印 SQL 语句
    
    Returns:
        Engine: SQLAlchemy 引擎实例
    """
    engine = create_engine(
        database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        pool_pre_ping=True,  # 自动检测失效连接
        echo=echo,
        connect_args={
            "connect_timeout": 30,
            "charset": "utf8mb4"
        }
    )
    
    # 注册事件监听器（可选，用于调试）
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
def get_session(engine: Engine) -> Session:
    """
    获取数据库会话（上下文管理器）
    
    使用示例:
        with get_session(engine) as session:
            result = session.query(Article).all()
    
    Args:
        engine: SQLAlchemy 引擎
    
    Yields:
        Session: 数据库会话
    """
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"数据库会话异常，已回滚: {e}")
        raise
    finally:
        session.close()


def get_pool_status(engine: Engine) -> dict:
    """
    获取连接池状态
    
    Args:
        engine: SQLAlchemy 引擎
    
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


def check_db_health(engine: Engine) -> bool:
    """
    检查数据库连接健康状态
    
    Args:
        engine: SQLAlchemy 引擎
    
    Returns:
        bool: 健康返回 True，否则返回 False
    """
    try:
        with get_session(engine) as session:
            session.execute(text("SELECT 1"))
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
    from models.article import Base
    
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
            Base.metadata.create_all(engine)
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
```

### 2.2 更新 main.py

```python
from utils.db_utils import init_database_with_retry, get_session
from config.settings import settings

# 初始化数据库引擎
engine = init_database_with_retry(
    database_url=settings.DATABASE_URL,
    db_name=settings.DB_NAME,
    db_host=settings.DB_HOST,
    db_port=settings.DB_PORT,
    db_user=settings.DB_USER,
    db_password=settings.DB_PASSWORD
)

# 使用会话
with get_session(engine) as session:
    # 执行数据库操作
    pass
```

### 2.3 更新所有使用 DatabaseConnectionPool 的代码

**查找并替换**:
```diff
- from utils.db_utils import DatabaseConnectionPool
- db_pool = DatabaseConnectionPool(...)
- with db_pool.get_session() as session:

+ from utils.db_utils import create_db_engine, get_session
+ engine = create_db_engine(...)
+ with get_session(engine) as session:
```

---

## 阶段 3: 迁移到 SQLModel（可选）

### 3.1 评估是否需要迁移

**迁移的好处**:
- 类型安全（完整的类型提示）
- 数据验证（Pydantic 集成）
- 代码简化（无需 BaseRepository）
- 更好的 IDE 支持

**迁移的成本**:
- 需要重写所有模型
- 需要更新所有 Repository
- 需要全面测试

**建议**: 如果项目处于早期阶段或计划长期维护，建议迁移。

### 3.2 安装依赖

```bash
pip install sqlmodel
```

### 3.3 重写 models/article.py

```python
"""
数据模型定义 - 使用 SQLModel

定义文章和提取项目的数据库模型
"""
from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime


class Article(SQLModel, table=True):
    """
    文章表
    
    存储从 RSS 源获取的文章元数据
    """
    __tablename__ = 'articles'
    
    id: Optional[int] = Field(default=None, primary_key=True, description='主键ID')
    title: str = Field(max_length=512, description='文章标题')
    url: str = Field(max_length=1024, description='文章链接')
    guid: str = Field(max_length=512, unique=True, index=True, description='文章唯一标识')
    feed_id: Optional[str] = Field(default=None, max_length=100, description='来源 feed ID')
    published_at: Optional[datetime] = Field(default=None, description='发布时间')
    fetched_at: datetime = Field(default_factory=datetime.utcnow, description='抓取时间')
    status: str = Field(default='pending', max_length=50, description='处理状态')
    summary: Optional[str] = Field(default=None, description='文章摘要')


class ExtractedProject(SQLModel, table=True):
    """
    提取项目表
    
    存储从文章中提取的结构化项目信息
    """
    __tablename__ = 'extracted_projects'
    
    id: Optional[int] = Field(default=None, primary_key=True, description='主键ID')
    article_id: int = Field(description='关联的文章ID')
    company_name: Optional[str] = Field(default=None, max_length=255, description='公司名称')
    province: Optional[str] = Field(default=None, max_length=100, description='省份')
    city: Optional[str] = Field(default=None, max_length=100, description='城市')
    client_type: Optional[str] = Field(default=None, max_length=100, description='客户类型')
    application_scene: Optional[str] = Field(default=None, max_length=100, description='应用场景')
    project_name: Optional[str] = Field(default=None, max_length=255, description='项目名称')
    project_stage: Optional[str] = Field(default=None, max_length=100, description='项目阶段')
    raw_json: Optional[dict] = Field(default=None, sa_column_kwargs={"type_": "JSON"}, description='原始 JSON 数据')
    created_at: datetime = Field(default_factory=datetime.utcnow, description='创建时间')
```

### 3.4 简化 repositories/article_repository.py

```python
"""
文章仓储类 - 使用 SQLModel

提供文章相关的数据访问方法
"""
from typing import Optional, List
from sqlmodel import Session, select
from models.article import Article, ExtractedProject


class ArticleRepository:
    """文章仓储类"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_by_id(self, id: int) -> Optional[Article]:
        """根据 ID 获取文章"""
        return self.session.get(Article, id)
    
    def get_by_guid(self, guid: str) -> Optional[Article]:
        """根据 GUID 获取文章"""
        statement = select(Article).where(Article.guid == guid)
        return self.session.exec(statement).first()
    
    def get_by_status(self, status: str, limit: Optional[int] = None) -> List[Article]:
        """根据状态获取文章列表"""
        statement = select(Article).where(Article.status == status)
        if limit:
            statement = statement.limit(limit)
        return list(self.session.exec(statement).all())
    
    def create(self, article: Article) -> Article:
        """创建文章"""
        self.session.add(article)
        self.session.flush()
        self.session.refresh(article)
        return article
    
    def update_status(self, article_id: int, status: str, summary: Optional[str] = None) -> bool:
        """更新文章状态"""
        article = self.get_by_id(article_id)
        if article:
            article.status = status
            if summary:
                article.summary = summary
            self.session.add(article)
            self.session.flush()
            return True
        return False


class ExtractedProjectRepository:
    """提取项目仓储类"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_by_article_id(self, article_id: int) -> Optional[ExtractedProject]:
        """根据文章 ID 获取提取项目"""
        statement = select(ExtractedProject).where(ExtractedProject.article_id == article_id)
        return self.session.exec(statement).first()
    
    def create(self, project: ExtractedProject) -> ExtractedProject:
        """创建提取项目"""
        self.session.add(project)
        self.session.flush()
        self.session.refresh(project)
        return project
```

### 3.5 删除 repositories/base.py

```bash
rm analysis-ollama/repositories/base.py
```

### 3.6 更新 utils/db_utils.py 使用 SQLModel

```python
from sqlmodel import create_engine, Session
from contextlib import contextmanager

def create_db_engine(database_url: str, echo: bool = False):
    """创建 SQLModel 引擎"""
    return create_engine(
        database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=echo
    )

@contextmanager
def get_session(engine):
    """获取 SQLModel 会话"""
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
```

---

## 测试清单

### 阶段 1 测试（Loguru）

- [ ] 日志正常输出到控制台
- [ ] 日志级别过滤正常工作
- [ ] JSON 格式输出正确（生产环境）
- [ ] 异常堆栈正确显示
- [ ] 所有模块的日志正常工作

### 阶段 2 测试（简化连接池）

- [ ] 数据库连接正常
- [ ] 连接池正常工作
- [ ] 会话管理正常（commit/rollback）
- [ ] 健康检查正常
- [ ] 连接池状态查询正常

### 阶段 3 测试（SQLModel）

- [ ] 模型定义正确
- [ ] 数据验证正常工作
- [ ] CRUD 操作正常
- [ ] 类型提示正确
- [ ] 所有业务逻辑正常

---

## 回滚计划

如果迁移出现问题，可以快速回滚：

1. **Loguru 回滚**: 恢复旧的 `utils/logger.py` 和导入语句
2. **连接池回滚**: 恢复旧的 `DatabaseConnectionPool` 类
3. **SQLModel 回滚**: 恢复旧的 models 和 repositories

建议使用 Git 分支进行迁移，确保可以随时回滚。

---

## 总结

按照本指南逐步实施，可以将项目迁移到业界推荐的最佳实践框架，提高代码质量和可维护性。
