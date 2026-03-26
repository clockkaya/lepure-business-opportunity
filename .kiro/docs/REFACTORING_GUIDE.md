# 重构指南

## 项目结构重构说明

本项目已完成大规模重构，采用分层架构设计，提升代码质量和可维护性。

## 新的项目结构

```
analysis-ollama/
├── config/              # 配置层
│   └── settings.py      # 环境变量配置和验证
├── models/              # 数据模型层
│   ├── __init__.py
│   └── article.py       # Article 和 ExtractedProject 模型
├── repositories/        # 数据访问层
│   ├── __init__.py
│   ├── base.py          # 基础仓储类（通用 CRUD）
│   └── article_repository.py  # 文章仓储（特定查询）
├── services/            # 业务逻辑层
│   ├── __init__.py
│   ├── rss_service.py   # RSS 采集服务（同步/异步）
│   ├── llm_service.py   # LLM 分析服务
│   └── notification_service.py  # 通知服务
├── utils/               # 工具层
│   ├── __init__.py
│   ├── logger.py        # 日志配置
│   ├── html_parser.py   # HTML 清洗
│   └── db_utils.py      # 数据库连接池管理
├── core/                # 核心业务编排层
│   ├── __init__.py
│   ├── processor.py     # 主处理流程编排
│   └── health_check.py  # 健康检查
├── scripts/             # 脚本
├── docs/                # 文档
├── tests/               # 测试
└── main.py              # 程序入口
```

## 主要改进

### 1. 数据库连接池改进

**旧方式 (core/db_repo.py):**
- 简单的 SQLAlchemy 引擎创建
- 基本的连接池配置
- 缺少监控和统计

**新方式 (utils/db_utils.py):**
- 使用 `QueuePool` 显式配置（类似 Java 的 HikariCP）
- 连接池监控和统计（checkout/checkin/connect/disconnect 事件）
- 提供 `get_pool_status()` 和 `log_pool_status()` 方法
- 上下文管理器支持 (`with db_pool.get_session()`)
- 健康检查功能

**使用示例:**
```python
from utils.db_utils import init_database_with_retry

# 初始化连接池
db_pool = init_database_with_retry(
    database_url=settings.database_url,
    db_name=settings.DB_NAME,
    db_host=settings.DB_HOST,
    db_port=settings.DB_PORT,
    db_user=settings.DB_USER,
    db_password=settings.DB_PASSWORD
)

# 使用上下文管理器
with db_pool.get_session() as session:
    articles = session.query(Article).all()

# 查看连接池状态
db_pool.log_pool_status()
```

### 2. 分层架构

**配置层 (config/):**
- 集中管理环境变量
- Pydantic 验证
- 类型安全

**数据模型层 (models/):**
- SQLAlchemy 模型定义
- 与业务逻辑分离

**数据访问层 (repositories/):**
- 封装数据库操作
- 提供通用 CRUD（BaseRepository）
- 特定查询方法（ArticleRepository）

**业务逻辑层 (services/):**
- RSS 采集逻辑
- LLM 分析逻辑
- 通知发送逻辑
- 支持同步和异步操作

**工具层 (utils/):**
- 日志配置
- HTML 解析
- 数据库连接池管理

**核心编排层 (core/):**
- 协调各个服务
- 主处理流程
- 健康检查

### 3. 移除 sys.path 操作

**旧方式:**
```python
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings
```

**新方式:**
```python
from config.settings import settings
```

**运行方式:**
```bash
# 旧方式
python main.py

# 新方式（推荐）
python -m main

# 或者在项目根目录
cd analysis-ollama
python main.py
```

### 4. 多公众号异步处理支持

**新增功能 (services/rss_service.py):**
- `fetch_all_feeds_async()`: 异步获取所有订阅的公众号
- `process_feed_async()`: 异步处理单个公众号
- 并发控制（Semaphore）：最多同时处理 5 个公众号
- 使用 `aiohttp` 进行异步 HTTP 请求

**使用示例:**
```python
import asyncio
from services.rss_service import RSSService

rss_service = RSSService(settings.WEWE_RSS_URL, settings.AUTH_CODE)

# 异步获取所有 feed 的文章
feed_articles = await rss_service.fetch_all_feeds_async(max_concurrent=5)

# 结果格式: {'feed_123': [article1, article2, ...], 'feed_456': [...]}
for feed_id, articles in feed_articles.items():
    print(f"Feed {feed_id}: {len(articles)} 篇文章")
```

### 5. 注释中文化

所有代码注释、docstring 和日志消息已改为中文，提升可读性。

## 依赖更新

新增依赖：
- `sqlalchemy-utils==0.41.1`: SQLAlchemy 工具库
- `aiohttp==3.9.1`: 异步 HTTP 客户端
- `asyncio==3.4.3`: 异步 I/O 支持

## 迁移指南

### 从旧代码迁移

**1. 导入路径变更:**

| 旧路径 | 新路径 |
|--------|--------|
| `from core.models import Article` | `from models.article import Article` |
| `from core.db_repo import SessionLocal` | `from utils.db_utils import DatabaseConnectionPool` |
| `from core.rss_collector import fetch_feed_articles` | `from services.rss_service import RSSService` |
| `from core.llm_analyzer import analyze_article_with_llm` | `from services.llm_service import LLMService` |
| `from core.notification import send_wecom_message` | `from services.notification_service import NotificationService` |
| `from core.html_parser import clean_html` | `from utils.html_parser import clean_html` |
| `from core.logger import setup_logging` | `from utils.logger import setup_logging` |

**2. 数据库会话使用:**

旧方式:
```python
from core.db_repo import SessionLocal

session = SessionLocal()
try:
    # 操作
    session.commit()
except:
    session.rollback()
finally:
    session.close()
```

新方式:
```python
from utils.db_utils import init_database_with_retry

db_pool = init_database_with_retry(...)

with db_pool.get_session() as session:
    # 操作（自动 commit/rollback/close）
    pass
```

**3. 服务使用:**

旧方式:
```python
from core.rss_collector import fetch_feed_articles
from core.llm_analyzer import analyze_article_with_llm

articles = fetch_feed_articles()
result = analyze_article_with_llm(title, content)
```

新方式:
```python
from services.rss_service import RSSService
from services.llm_service import LLMService

rss_service = RSSService(settings.WEWE_RSS_URL, settings.AUTH_CODE)
llm_service = LLMService(settings.OLLAMA_BASE_URL, settings.MODEL_NAME)

articles = rss_service.fetch_feed_articles()
result = llm_service.analyze_article(title, content)
```

## 测试

更新测试文件以使用新的导入路径：

```python
# tests/test_settings.py
from config.settings import settings

# tests/test_repositories.py
from models.article import Article
from repositories.article_repository import ArticleRepository

# tests/test_services.py
from services.rss_service import RSSService
from services.llm_service import LLMService
```

## 未来扩展

### 多公众号支持

当前版本使用环境变量配置单个 feed。未来可以启用以下功能：

1. **启用 FeedConfig 模型** (models/article.py):
   - 取消注释 `FeedConfig` 类
   - 运行数据库迁移

2. **使用动态 webhook 路由** (services/notification_service.py):
   - 取消注释 `DynamicNotificationService` 类
   - 根据 feed_id 路由到不同的企业微信群

3. **异步处理多个 feed**:
   ```python
   # 使用已实现的异步方法
   feed_articles = await rss_service.fetch_all_feeds_async(max_concurrent=5)
   ```

## 常见问题

### Q: 如何运行项目？

A: 推荐使用以下方式：
```bash
cd analysis-ollama
python main.py
```

或者：
```bash
python -m main
```

### Q: 导入错误怎么办？

A: 确保：
1. 在项目根目录运行
2. 所有 `__init__.py` 文件存在
3. 使用相对导入（不要使用 `sys.path.append`）

### Q: 如何查看连接池状态？

A:
```python
db_pool.log_pool_status()
# 或
status = db_pool.get_pool_status()
print(status)
```

### Q: 如何启用异步多公众号处理？

A: 参考 `services/rss_service.py` 中的 `fetch_all_feeds_async()` 方法，并在 `main.py` 中使用 `asyncio.run()`。

## 总结

本次重构带来的主要优势：

1. **更清晰的代码组织**: 分层架构，职责分明
2. **更好的可维护性**: 模块化设计，易于扩展
3. **更专业的数据库管理**: 连接池监控和统计
4. **异步支持**: 为多公众号并发处理做好准备
5. **更好的可读性**: 中文注释和文档
6. **更规范的导入**: 移除 sys.path 操作

如有问题，请参考各模块的 docstring 或联系开发团队。
