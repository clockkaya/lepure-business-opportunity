# 设计文档

## 概述

本设计文档描述了 lepure-business-opportunity（CGT MI 工具）项目从"Docker + 本地混合"模式向"环境分离架构"的改造方案。改造后的架构将实现：

- **基础服务层（Base Service Layer）**: wewe-rss 及其 MySQL 数据库作为独立服务持续运行，不区分环境
- **应用服务层（Application Service Layer）**: analysis-ollama 支持 dev/pre 环境配置，可容器化部署
- **清晰的服务依赖**: 通过 Docker 网络实现服务间通信，支持灵活的环境切换

### 设计目标

1. **环境隔离**: 开发环境（dev）和预发布环境（pre）配置分离，互不干扰
2. **容器化部署**: analysis-ollama 完全容器化，便于打包、分发和部署
3. **网络互通**: 通过 Docker 网络实现服务间的可靠通信
4. **配置管理**: 使用环境变量和配置文件管理不同环境的参数
5. **可维护性**: 清晰的代码结构、完善的日志和文档
6. **可扩展性**: 支持多个公众号、不同的 webhook 和不同的推送频率

### 关键技术栈

- **WeWe-RSS**: NestJS + React + MySQL + Docker Compose
- **Analysis-Ollama**: Python 3.10+ + SQLAlchemy + Docker
- **容器编排**: Docker Compose
- **网络**: Docker Bridge Network
- **配置管理**: python-dotenv + pydantic-settings

## 架构

### 整体架构

系统采用分层架构，分为基础服务层和应用服务层：

```
┌─────────────────────────────────────────────────────────────┐
│                     External Services                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Ollama     │  │  WeCom API   │  │  WeRead      │      │
│  │ 192.168.10.43│  │   Webhook    │  │   Platform   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────┼───────────────────────────────┐
│         Application Service Layer                            │
│  ┌──────────────────────────┴────────────────────────────┐  │
│  │          analysis-ollama (Python App)                 │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │  │
│  │  │RSS Collect │  │HTML Parser │  │LLM Analyzer│     │  │
│  │  └────────────┘  └────────────┘  └────────────┘     │  │
│  │  ┌────────────┐  ┌────────────┐                      │  │
│  │  │  DB Repo   │  │Notification│                      │  │
│  │  └────────────┘  └────────────┘                      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ Docker Network (wewe-rss_default)
┌─────────────────────────────┼───────────────────────────────┐
│           Base Service Layer                                 │
│  ┌──────────────────────────┴────────────────────────────┐  │
│  │              wewe-rss (NestJS + React)                │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │  │
│  │  │  Web UI    │  │  API       │  │  Scheduler │     │  │
│  │  │  :4000     │  │  /feeds    │  │  (Cron)    │     │  │
│  │  └────────────┘  └────────────┘  └────────────┘     │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              MySQL 8.0 Database                       │  │
│  │              Port: 3308 (host) / 3306 (container)     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 环境架构

#### 开发环境（Dev）

```
┌─────────────────────────────────────────────────────────────┐
│                        Host Machine                          │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  analysis-ollama Container (dev)                       │ │
│  │  - Mounts: ./analysis-ollama:/app                      │ │
│  │  - Network: wewe-rss_default (external)                │ │
│  │  - Env: .env.dev                                       │ │
│  │  - DB: 127.0.0.1:3308 (via host.docker.internal)      │ │
│  │  - WeWe-RSS: http://app:4000                           │ │
│  └────────────────────────────────────────────────────────┘ │
│                          ▲                                   │
│                          │ Docker Network                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  wewe-rss Containers                                   │ │
│  │  ┌──────────────┐  ┌──────────────┐                   │ │
│  │  │  app:4000    │  │  db:3306     │                   │ │
│  │  │              │  │  (->3308)    │                   │ │
│  │  └──────────────┘  └──────────────┘                   │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  Local Code: ./analysis-ollama/                              │
│  (Hot reload enabled)                                        │
└─────────────────────────────────────────────────────────────┘
```

#### 预发布环境（Pre）

```
┌─────────────────────────────────────────────────────────────┐
│                        Host Machine                          │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  analysis-ollama Container (pre)                       │ │
│  │  - Image: analysis-ollama:latest                       │ │
│  │  - Network: wewe-rss_default (external)                │ │
│  │  - Env: .env.pre                                       │ │
│  │  - DB: db:3306 (via Docker network)                    │ │
│  │  - WeWe-RSS: http://app:4000                           │ │
│  └────────────────────────────────────────────────────────┘ │
│                          ▲                                   │
│                          │ Docker Network                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  wewe-rss Containers                                   │ │
│  │  ┌──────────────┐  ┌──────────────┐                   │ │
│  │  │  app:4000    │  │  db:3306     │                   │ │
│  │  │              │  │  (->3308)    │                   │ │
│  │  └──────────────┘  └──────────────┘                   │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 网络设计

#### Docker 网络配置

- **网络名称**: `wewe-rss_default`（由 wewe-rss 的 docker-compose 自动创建）
- **网络类型**: bridge
- **DNS 解析**: 容器间通过服务名称进行通信（如 `db`、`app`）

#### 服务发现

- **wewe-rss 内部**: `app` 容器通过 `db:3306` 访问 MySQL（数据库名: `wewe-rss`）
- **analysis-ollama -> wewe-rss**: 通过 `http://app:4000` 访问 API
- **analysis-ollama -> MySQL**:
  - Dev: `127.0.0.1:3308`（通过宿主机端口映射，数据库名: `analysis_ollama`）
  - Pre: `db:3306`（通过 Docker 网络，数据库名: `analysis_ollama`）
  
**注意**: analysis-ollama 和 wewe-rss 使用同一个 MySQL 实例，但使用不同的数据库：
- wewe-rss 使用 `wewe-rss` 数据库
- analysis-ollama 使用 `analysis_ollama` 数据库

#### 外部服务访问

- **Ollama**: `http://192.168.10.43:11434`（局域网服务）
- **企业微信 Webhook**: HTTPS 公网 API
- **微信读书平台**: `https://weread.965111.xyz`

### 启动顺序和依赖

```
1. 启动 wewe-rss
   └─> docker-compose up -d (in wewe-rss/)
       ├─> MySQL 容器启动并完成健康检查
       └─> WeWe-RSS 应用容器启动

2. 人工配置 wewe-rss（重要：必须等待此步骤完成）
   └─> 访问 http://localhost:4000
       ├─> 登录微信读书账号
       └─> 订阅目标公众号
       └─> 等待文章开始抓取

3. 验证 wewe-rss 正常运行
   └─> 检查 RSS feed: http://localhost:4000/feeds/{feedId}
   └─> 确认能够获取到文章列表

4. 启动 analysis-ollama（仅在步骤 2-3 完成后）
   └─> docker-compose -f docker-compose.dev.yml up -d (dev)
       或
       docker-compose up -d (pre)
   └─> analysis-ollama 将开始处理 wewe-rss 中的文章
```

**关键注意事项**:
- 步骤 2 和 3 必须由人工完成，不能自动化
- 在 wewe-rss 完成订阅配置并开始抓取文章之前，不要启动 analysis-ollama
- analysis-ollama 启动后会立即尝试连接 wewe-rss API，如果 wewe-rss 未就绪会导致错误

## 组件和接口

### WeWe-RSS 组件

#### 职责
- 微信公众号文章抓取
- RSS/Atom feed 生成
- Web 管理界面
- 数据持久化（MySQL）

#### 对外接口

**1. RSS Feed API**
```
GET /feeds/{feedId}
Response: application/xml (RSS 2.0 / Atom)

示例:
GET http://localhost:4000/feeds/123?auth_code=123567

返回字段:
- title: 文章标题
- link: 文章链接
- guid: 全局唯一标识符
- pubDate: 发布时间
- description: 文章 HTML 内容
```

**2. Web UI**
```
GET http://localhost:4000
- 登录界面
- 订阅管理
- Feed 列表
```

#### 数据库表（wewe-rss 内部）
- `Feed`: 订阅源信息
- `FeedItem`: 文章条目
- `Account`: 微信读书账号

### Analysis-Ollama 组件

#### 模块结构

```
analysis-ollama/
├── config/
│   └── settings.py          # 配置管理（pydantic-settings）
├── core/
│   ├── db_repo.py           # 数据库连接池和健康检查
│   ├── models.py            # SQLAlchemy ORM 模型
│   ├── rss_collector.py     # RSS 文章采集
│   ├── html_parser.py       # HTML 清洗和文本提取
│   ├── llm_analyzer.py      # LLM 信息提取
│   └── notification.py      # 企业微信通知
└── main.py                  # 应用入口和调度器
```

#### 1. 配置管理模块（config/settings.py）

**职责**: 加载和验证环境配置

**接口**:
```python
class Settings(BaseSettings):
    # 环境标识
    ENV: str = "dev"  # "dev" | "pre"
    
    # 轮询间隔
    POLL_INTERVAL_MINUTES: int = 60
    
    # WeWe-RSS 配置
    WEWE_RSS_URL: str
    AUTH_CODE: str
    
    # 数据库配置
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str = "analysis_ollama"  # 默认数据库名
    
    # AI 引擎配置
    OLLAMA_BASE_URL: str
    MODEL_NAME: str
    
    # 通知配置
    WECOM_WEBHOOK_URL: str
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    
    @property
    def database_url(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
```

**扩展性设计**:

为了支持多个公众号、不同的 webhook 和不同的推送频率，设计采用以下扩展方案：

1. **Feed 配置表（未来扩展）**:
```python
class FeedConfig(Base):
    __tablename__ = 'feed_configs'
    
    id = Column(Integer, primary_key=True)
    feed_id = Column(String(100), unique=True, nullable=False)  # WeWe-RSS 中的 feed ID
    feed_name = Column(String(255), nullable=False)  # 公众号名称
    webhook_url = Column(String(1024), nullable=False)  # 企业微信 Webhook URL
    poll_interval_minutes = Column(Integer, default=60)  # 轮询间隔（分钟）
    enabled = Column(Boolean, default=True)  # 是否启用
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
```

2. **多 Feed 采集策略**:
- 当前版本：从单个 feed 采集（通过环境变量配置）
- 扩展版本：从 `feed_configs` 表读取所有启用的 feed，分别采集和处理
- 每个 feed 可以配置独立的 webhook URL 和轮询间隔

3. **差异化推送频率**:
- 使用 `schedule` 库为每个 feed 配置独立的定时任务
- 示例：
  ```python
  for feed_config in feed_configs:
      schedule.every(feed_config.poll_interval_minutes).minutes.do(
          process_feed, feed_id=feed_config.feed_id
      )
  ```

4. **Webhook 路由**:
- 在 `ExtractedProject` 表中添加 `feed_id` 字段，关联到来源 feed
- 发送通知时，根据 `feed_id` 查找对应的 `webhook_url`
- 支持不同公众号推送到不同的企业微信群

**当前实现（MVP）**:
- 单个 feed，单个 webhook，固定轮询间隔
- 通过环境变量配置

**未来扩展路径**:
1. 添加 `feed_configs` 表和管理界面
2. 修改 `rss_collector` 支持多 feed 采集
3. 修改 `notification` 支持动态 webhook 路由
4. 添加 feed 级别的统计和监控

**配置加载顺序**:
1. 从 `.env` 文件加载（python-dotenv）
2. 从环境变量覆盖
3. 使用默认值（如果未配置）

#### 2. 数据库仓库模块（core/db_repo.py）

**职责**: 数据库连接管理、健康检查、重试机制

**接口**:
```python
def init_db() -> sessionmaker:
    """
    初始化数据库连接
    - 创建数据库（如果不存在）
    - 创建表结构（通过 SQLAlchemy ORM）
    - 返回 Session 工厂
    
    重试策略:
    - 最多重试 3 次
    - 每次间隔 5 秒
    - 失败后抛出异常
    """
    pass

def check_db_health() -> bool:
    """
    检查数据库连接健康状态
    - 执行简单查询（SELECT 1）
    - 返回 True/False
    """
    pass

SessionLocal: sessionmaker
```

**连接池配置**:
```python
engine = create_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True,
    connect_args={
        "connect_timeout": 30,
        "charset": "utf8mb4"
    }
)
```

#### 3. 数据模型模块（core/models.py）

**职责**: 定义 ORM 模型

**接口**: 见"数据模型"章节

#### 4. RSS 采集模块（core/rss_collector.py）

**职责**: 从 wewe-rss 获取文章列表

**接口**:
```python
def fetch_feed_articles() -> List[Dict[str, Any]]:
    """
    从 wewe-rss 获取 RSS feed
    
    Returns:
        List[Dict]: 文章列表
        [
            {
                "title": str,
                "url": str,
                "guid": str,
                "published_at": datetime,
                "html": str
            },
            ...
        ]
    
    Raises:
        requests.RequestException: 网络请求失败
        ValueError: RSS 解析失败
    """
    pass
```

**实现细节**:
- 使用 `requests` 库发送 HTTP GET 请求
- 解析 XML 格式的 RSS feed（使用 `xml.etree.ElementTree` 或 `feedparser`）
- 提取 `title`、`link`、`guid`、`pubDate`、`description` 字段
- 将 `pubDate` 转换为 `datetime` 对象
- 超时设置: 30 秒

#### 5. HTML 解析模块（core/html_parser.py）

**职责**: 清洗 HTML 内容，提取纯文本

**接口**:
```python
def clean_html(html_content: str) -> str:
    """
    清洗 HTML 内容，提取纯文本
    
    Args:
        html_content: 原始 HTML 字符串
    
    Returns:
        str: 清洗后的纯文本
    
    处理步骤:
    1. 移除 <script>、<style> 标签
    2. 移除 HTML 标签
    3. 解码 HTML 实体（&nbsp; -> 空格）
    4. 移除多余空白字符
    5. 保留段落结构（\n\n）
    """
    pass
```

**实现细节**:
- 使用 `BeautifulSoup` 解析 HTML
- 使用 `get_text()` 提取文本
- 使用正则表达式清理空白字符

#### 6. LLM 分析模块（core/llm_analyzer.py）

**职责**: 调用 Ollama LLM 提取结构化信息

**接口**:
```python
def analyze_article_with_llm(title: str, content: str) -> Optional[Dict[str, Any]]:
    """
    使用 LLM 分析文章，提取结构化信息
    
    Args:
        title: 文章标题
        content: 文章纯文本内容
    
    Returns:
        Dict | None: 提取的结构化数据
        {
            "company_name": str | None,
            "province": str | None,
            "city": str | None,
            "client_type": str | None,
            "application_scene": str | None,
            "project_name": str | None,
            "project_stage": str | None,
            "summary": str
        }
        
        如果 LLM 调用失败或超时，返回 None
    
    Raises:
        requests.RequestException: Ollama API 调用失败
        json.JSONDecodeError: LLM 返回格式错误
    """
    pass
```

**Prompt 设计**:
```
你是一个专业的信息提取助手。请从以下文章中提取企业项目相关信息：

标题: {title}
内容: {content}

请提取以下字段（如果文章中没有相关信息，字段值为 null）：
1. company_name: 公司名称
2. province: 省份
3. city: 城市
4. client_type: 客户类型（如：政府、企业、医院等）
5. application_scene: 应用场景（如：智慧城市、医疗信息化等）
6. project_name: 项目名称
7. project_stage: 项目阶段（如：签约、中标、上线等）
8. summary: 文章摘要（100字以内）

请以 JSON 格式返回，不要包含任何其他文字。
```

**实现细节**:
- 使用 `requests.post()` 调用 Ollama API
- 端点: `{OLLAMA_BASE_URL}/api/generate`
- 超时设置: 120 秒
- 重试策略: 失败后不重试，直接返回 None

#### 7. 通知模块（core/notification.py）

**职责**: 发送企业微信通知

**接口**:
```python
def send_wecom_message(project_data: Dict[str, Any], title: str, url: str) -> bool:
    """
    发送企业微信通知
    
    Args:
        project_data: 提取的项目数据
        title: 文章标题
        url: 文章链接
    
    Returns:
        bool: 发送成功返回 True，失败返回 False
    
    消息格式:
        【CGT MI 情报】
        公司: {company_name}
        地区: {province} {city}
        项目: {project_name}
        阶段: {project_stage}
        
        摘要: {summary}
        
        详情: {url}
    """
    pass
```

**实现细节**:
- 使用 `requests.post()` 发送 Webhook 请求
- 消息类型: `markdown`
- 超时设置: 10 秒
- 错误处理: 记录日志，不抛出异常

#### 8. 主程序模块（main.py）

**职责**: 应用入口、调度器、业务流程编排

**接口**:
```python
def process_routine() -> None:
    """
    执行一次完整的处理流程
    
    流程:
    1. 从 wewe-rss 获取文章列表
    2. 过滤已处理的文章（通过 guid 去重）
    3. 对每篇新文章:
       a. 插入 Article 记录（status='pending'）
       b. 清洗 HTML 内容
       c. 调用 LLM 分析
       d. 插入 ExtractedProject 记录
       e. 更新 Article 状态（'processed' 或 'error'）
       f. 发送企业微信通知（如果有 company_name）
    4. 提交事务
    
    异常处理:
    - 捕获所有异常
    - 回滚事务
    - 记录错误日志
    - 继续运行（不退出）
    """
    pass

if __name__ == "__main__":
    # 启动时立即执行一次
    process_routine()
    
    # 配置定时任务
    schedule.every(settings.POLL_INTERVAL_MINUTES).minutes.do(process_routine)
    
    # 主循环
    while True:
        schedule.run_pending()
        time.sleep(60)
```

### 容器健康检查

#### analysis-ollama 健康检查

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "from core.db_repo import check_db_health; import sys; sys.exit(0 if check_db_health() else 1)"
```

## 数据模型

### articles 表

**用途**: 存储从 wewe-rss 获取的文章元数据

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INT | PRIMARY KEY, AUTO_INCREMENT | 主键 |
| title | VARCHAR(512) | NOT NULL | 文章标题 |
| url | VARCHAR(1024) | NOT NULL | 文章链接 |
| guid | VARCHAR(512) | NOT NULL, UNIQUE | 全局唯一标识符（来自 RSS feed） |
| feed_id | VARCHAR(100) | NULL | 来源 feed ID（用于多公众号扩展） |
| published_at | DATETIME | NULL | 发布时间 |
| fetched_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 抓取时间 |
| status | VARCHAR(50) | NOT NULL, DEFAULT 'pending' | 处理状态: 'pending', 'processed', 'error' |
| summary | TEXT | NULL | 文章摘要（由 LLM 生成） |

**索引**:
- PRIMARY KEY: `id`
- UNIQUE INDEX: `guid`
- INDEX: `status`
- INDEX: `fetched_at`
- INDEX: `feed_id`（用于多公众号查询）

**DDL**:
```sql
CREATE TABLE IF NOT EXISTS `articles` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `title` VARCHAR(512) NOT NULL,
  `url` VARCHAR(1024) NOT NULL,
  `guid` VARCHAR(512) NOT NULL,
  `feed_id` VARCHAR(100) NULL COMMENT '来源 feed ID，用于多公众号扩展',
  `published_at` DATETIME NULL,
  `fetched_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `status` VARCHAR(50) NOT NULL DEFAULT 'pending',
  `summary` TEXT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_guid` (`guid`),
  INDEX `idx_status` (`status`),
  INDEX `idx_fetched_at` (`fetched_at`),
  INDEX `idx_feed_id` (`feed_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### extracted_projects 表

**用途**: 存储从文章中提取的结构化项目信息

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INT | PRIMARY KEY, AUTO_INCREMENT | 主键 |
| article_id | INT | NOT NULL | 关联的文章 ID（外键） |
| company_name | VARCHAR(255) | NULL | 公司名称 |
| province | VARCHAR(100) | NULL | 省份 |
| city | VARCHAR(100) | NULL | 城市 |
| client_type | VARCHAR(100) | NULL | 客户类型 |
| application_scene | VARCHAR(100) | NULL | 应用场景 |
| project_name | VARCHAR(255) | NULL | 项目名称 |
| project_stage | VARCHAR(100) | NULL | 项目阶段 |
| raw_json | JSON | NULL | LLM 返回的原始 JSON 数据 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引**:
- PRIMARY KEY: `id`
- INDEX: `article_id`
- INDEX: `company_name`
- INDEX: `province`, `city`
- INDEX: `created_at`

**DDL**:
```sql
CREATE TABLE IF NOT EXISTS `extracted_projects` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `article_id` INT NOT NULL,
  `company_name` VARCHAR(255) NULL,
  `province` VARCHAR(100) NULL,
  `city` VARCHAR(100) NULL,
  `client_type` VARCHAR(100) NULL,
  `application_scene` VARCHAR(100) NULL,
  `project_name` VARCHAR(255) NULL,
  `project_stage` VARCHAR(100) NULL,
  `raw_json` JSON NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_article_id` (`article_id`),
  INDEX `idx_company_name` (`company_name`),
  INDEX `idx_location` (`province`, `city`),
  INDEX `idx_created_at` (`created_at`),
  CONSTRAINT `fk_article` FOREIGN KEY (`article_id`) REFERENCES `articles` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 数据流

```
1. RSS Feed (wewe-rss)
   └─> fetch_feed_articles()
       └─> Article (status='pending')

2. Article
   └─> clean_html()
       └─> analyze_article_with_llm()
           └─> ExtractedProject
               └─> Article (status='processed')
                   └─> send_wecom_message()
```


## 正确性属性

*属性是一个特征或行为，应该在系统的所有有效执行中保持为真——本质上是关于系统应该做什么的形式化陈述。属性作为人类可读规范和机器可验证正确性保证之间的桥梁。*

### 属性 1: 配置驱动的环境行为

*对于任何*有效的环境配置（dev 或 pre），当应用使用该配置启动时，应用的行为（数据库连接地址、API 端点）应该与配置中指定的值一致，而无需修改代码。

**验证需求: 2.1, 2.7, 3.5, 5.8, 12.14**

### 属性 2: 数据库连接重试机制

*对于任何*数据库连接失败的情况，系统应该最多重试 3 次（每次间隔 5 秒），如果所有重试都失败，则记录错误并优雅退出。

**验证需求: 7.5, 12.5, 12.6**

### 属性 3: 结构化日志完整性

*对于任何*关键操作（RSS 采集、HTML 解析、LLM 分析、通知发送），系统应该输出包含时间戳、日志级别、模块名称和消息内容的结构化日志；对于任何异常，应该记录完整的错误堆栈信息。

**验证需求: 9.1, 9.2, 9.4, 9.5, 12.13**

### 属性 4: 容器数据持久化

*对于任何*写入 MySQL 数据库的数据，当容器重启后，数据应该仍然存在且可读取（通过持久化卷实现）。

**验证需求: 1.4**

### 属性 5: 数据库读写往返

*对于任何*有效的 Article 对象，当将其存储到数据库后再读取，应该得到等价的数据（所有字段值相同）。

**验证需求: 11.10**

### 属性 6: GUID 唯一性约束

*对于任何*已存在于数据库中的 guid 值，尝试插入具有相同 guid 的新记录应该失败（由唯一索引强制执行）。

**验证需求: 11.6**

### 属性 7: 依赖服务不可用时的错误处理

*对于任何*外部依赖服务（WeWe-RSS API、Ollama、企业微信 Webhook）不可用的情况，系统应该记录明确的错误信息，并根据服务类型采取适当的处理策略（重试、跳过、退出）。

**验证需求: 8.8**

## 错误处理

### 错误分类

#### 1. 配置错误（启动时失败）

**场景**: 必需的环境变量未配置或配置值无效

**处理策略**:
- 在应用启动时验证所有必需配置
- 输出清晰的错误消息，指明缺失或无效的配置项
- 退出应用（exit code 1）

**示例**:
```
ERROR: Missing required configuration: WEWE_RSS_URL
Please set the WEWE_RSS_URL environment variable in your .env file.
Example: WEWE_RSS_URL=http://localhost:4000
```

#### 2. 数据库连接错误（启动时失败）

**场景**: 无法连接到 MySQL 数据库

**处理策略**:
- 实现重试机制：最多重试 3 次，每次间隔 5 秒
- 记录每次重试的详细错误信息
- 如果所有重试都失败，输出明确的错误消息并退出

**示例**:
```
WARNING: Failed to connect to database at 127.0.0.1:3308 (attempt 1/3)
Error: Can't connect to MySQL server on '127.0.0.1' (111)
Retrying in 5 seconds...

ERROR: Failed to connect to database after 3 attempts
Please check:
1. MySQL service is running
2. DB_HOST and DB_PORT are correct
3. DB_USER and DB_PASSWORD are valid
```

#### 3. WeWe-RSS API 错误（运行时错误）

**场景**: 
- WeWe-RSS 服务不可用
- API 返回错误状态码
- 网络超时

**处理策略**:
- 记录错误日志
- 跳过本次轮询，等待下次调度
- 不退出应用（保持运行）

**示例**:
```
ERROR: Failed to fetch RSS feed from http://app:4000/feeds/123
Status code: 503 Service Unavailable
Skipping this polling cycle. Will retry in 60 minutes.
```

#### 4. HTML 解析错误（运行时错误）

**场景**: HTML 内容格式异常或为空

**处理策略**:
- 记录警告日志
- 返回空字符串或原始内容
- 继续处理（不中断流程）

**示例**:
```
WARNING: Failed to parse HTML content for article: "文章标题"
Using raw content as fallback.
```

#### 5. LLM 分析错误（运行时错误）

**场景**:
- Ollama 服务不可用
- LLM 请求超时（>120 秒）
- LLM 返回格式错误（非 JSON）

**处理策略**:
- 记录错误日志
- 将文章状态标记为 'error'
- 不插入 ExtractedProject 记录
- 继续处理下一篇文章

**示例**:
```
ERROR: LLM analysis failed for article: "文章标题"
Error: Connection timeout after 120 seconds
Article marked as 'error' and will be skipped.
```

#### 6. 企业微信通知错误（运行时错误）

**场景**:
- Webhook URL 无效
- 网络请求失败
- API 返回错误

**处理策略**:
- 记录错误日志
- 不影响文章处理流程（已提取的数据仍然保存）
- 不重试（避免重复通知）

**示例**:
```
ERROR: Failed to send WeCom notification
Error: HTTPSConnectionPool(host='qyapi.weixin.qq.com', port=443): Max retries exceeded
Article data has been saved to database.
```

### 错误日志格式

所有错误日志应包含以下信息：
- 时间戳（ISO 8601 格式）
- 日志级别（ERROR、WARNING）
- 模块名称
- 错误消息
- 上下文信息（如文章标题、URL）
- 错误堆栈（对于异常）

**示例**:
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "ERROR",
  "module": "core.llm_analyzer",
  "message": "LLM analysis failed",
  "context": {
    "article_title": "某公司签约智慧城市项目",
    "article_url": "https://example.com/article/123"
  },
  "error": "Connection timeout after 120 seconds",
  "traceback": "..."
}
```

### 健康检查

#### 启动时健康检查

在应用启动时，执行以下检查：

1. **配置验证**: 检查所有必需的环境变量
2. **数据库连接**: 验证数据库可访问并创建表结构
3. **WeWe-RSS 连通性**: 尝试访问 WeWe-RSS API（可选，失败不退出）

#### 运行时健康检查

提供健康检查端点或函数，用于容器健康检查：

```python
def check_health() -> bool:
    """
    检查应用健康状态
    
    Returns:
        bool: 健康返回 True，否则返回 False
    
    检查项:
    1. 数据库连接是否正常
    2. 调度器是否运行
    """
    try:
        # 检查数据库连接
        session = SessionLocal()
        session.execute("SELECT 1")
        session.close()
        return True
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False
```

## 测试策略

### 测试方法

本项目采用**双重测试方法**，结合单元测试和属性测试：

- **单元测试**: 验证特定示例、边缘情况和错误条件
- **属性测试**: 验证跨所有输入的通用属性
- 两者互补且都是必需的：单元测试捕获具体错误，属性测试验证一般正确性

### 单元测试

单元测试应专注于：
- 特定示例，展示正确行为
- 组件之间的集成点
- 边缘情况和错误条件

**不要编写过多的单元测试** - 属性测试已经处理了大量输入的覆盖。

#### 测试范围

**1. 配置管理测试**
```python
def test_load_dev_config():
    """测试加载开发环境配置"""
    os.environ['ENV'] = 'dev'
    settings = Settings()
    assert settings.DB_HOST == '127.0.0.1'
    assert settings.DB_PORT == 3308

def test_missing_required_config():
    """测试缺失必需配置时的错误处理"""
    # 移除必需的环境变量
    del os.environ['WEWE_RSS_URL']
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert 'WEWE_RSS_URL' in str(exc_info.value)
```

**2. 数据库连接测试**
```python
def test_database_connection():
    """测试数据库连接成功"""
    session = SessionLocal()
    result = session.execute("SELECT 1").scalar()
    assert result == 1
    session.close()

def test_database_retry_mechanism():
    """测试数据库连接重试机制"""
    # 使用错误的数据库配置
    with pytest.raises(Exception) as exc_info:
        # 应该重试 3 次后失败
        init_db_with_invalid_config()
    # 验证日志中有 3 次重试记录
```

**3. RSS 采集测试**
```python
def test_fetch_feed_articles_success():
    """测试成功获取 RSS feed"""
    articles = fetch_feed_articles()
    assert isinstance(articles, list)
    if len(articles) > 0:
        assert 'title' in articles[0]
        assert 'guid' in articles[0]

def test_fetch_feed_articles_network_error():
    """测试网络错误时的处理"""
    # Mock 网络错误
    with pytest.raises(requests.RequestException):
        fetch_feed_articles_with_invalid_url()
```

**4. HTML 解析测试**
```python
def test_clean_html_basic():
    """测试基本 HTML 清洗"""
    html = "<p>Hello <b>World</b></p>"
    text = clean_html(html)
    assert text == "Hello World"

def test_clean_html_empty():
    """测试空 HTML 内容"""
    text = clean_html("")
    assert text == ""

def test_clean_html_with_script():
    """测试移除 script 标签"""
    html = "<p>Content</p><script>alert('xss')</script>"
    text = clean_html(html)
    assert "alert" not in text
```

**5. 数据模型测试**
```python
def test_article_creation():
    """测试创建 Article 记录"""
    session = SessionLocal()
    article = Article(
        title="测试文章",
        url="https://example.com/test",
        guid="test-guid-123",
        status="pending"
    )
    session.add(article)
    session.commit()
    
    # 验证记录已创建
    saved = session.query(Article).filter(Article.guid == "test-guid-123").first()
    assert saved is not None
    assert saved.title == "测试文章"
    session.close()

def test_guid_uniqueness():
    """测试 guid 唯一性约束"""
    session = SessionLocal()
    article1 = Article(title="文章1", url="url1", guid="same-guid")
    session.add(article1)
    session.commit()
    
    # 尝试插入相同 guid
    article2 = Article(title="文章2", url="url2", guid="same-guid")
    session.add(article2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.close()
```

**6. 环境切换测试**
```python
def test_dev_environment_config():
    """测试开发环境配置"""
    os.environ['ENV'] = 'dev'
    settings = Settings()
    assert settings.DB_HOST == '127.0.0.1'
    assert settings.WEWE_RSS_URL == 'http://localhost:4000'

def test_pre_environment_config():
    """测试预发布环境配置"""
    os.environ['ENV'] = 'pre'
    settings = Settings()
    assert settings.DB_HOST == 'db'
    assert settings.WEWE_RSS_URL == 'http://app:4000'
```

### 属性测试

属性测试使用 **Hypothesis** 库（Python 的属性测试框架）。

#### 配置要求
- 每个属性测试最少运行 **100 次迭代**（由于随机化）
- 每个测试必须引用其设计文档属性
- 标签格式: **Feature: environment-separation-architecture, Property {number}: {property_text}**

#### 属性测试用例

**1. 属性 1: 配置驱动的环境行为**
```python
from hypothesis import given, strategies as st

@given(
    env=st.sampled_from(['dev', 'pre']),
    db_host=st.text(min_size=1, max_size=50),
    db_port=st.integers(min_value=1024, max_value=65535)
)
@settings(max_examples=100)
def test_property_config_driven_behavior(env, db_host, db_port):
    """
    Feature: environment-separation-architecture, Property 1: 配置驱动的环境行为
    
    对于任何有效的环境配置，应用行为应与配置一致
    """
    os.environ['ENV'] = env
    os.environ['DB_HOST'] = db_host
    os.environ['DB_PORT'] = str(db_port)
    
    settings = Settings()
    
    # 验证配置被正确加载
    assert settings.ENV == env
    assert settings.DB_HOST == db_host
    assert settings.DB_PORT == db_port
    
    # 验证数据库 URL 包含配置的值
    assert db_host in settings.database_url
    assert str(db_port) in settings.database_url
```

**2. 属性 3: 结构化日志完整性**
```python
@given(
    operation=st.sampled_from(['rss_collect', 'html_parse', 'llm_analyze', 'notification']),
    message=st.text(min_size=1, max_size=200)
)
@settings(max_examples=100)
def test_property_structured_logging(operation, message, caplog):
    """
    Feature: environment-separation-architecture, Property 3: 结构化日志完整性
    
    对于任何关键操作，日志应包含时间戳、级别、模块名称和消息
    """
    logger = logging.getLogger(f'core.{operation}')
    logger.info(message)
    
    # 验证日志记录
    assert len(caplog.records) > 0
    record = caplog.records[-1]
    
    # 验证日志包含必需字段
    assert record.levelname in ['DEBUG', 'INFO', 'WARNING', 'ERROR']
    assert record.name.startswith('core.')
    assert record.message == message
    assert hasattr(record, 'created')  # 时间戳
```

**3. 属性 5: 数据库读写往返**
```python
@given(
    title=st.text(min_size=1, max_size=512),
    url=st.text(min_size=1, max_size=1024),
    guid=st.text(min_size=1, max_size=512),
    status=st.sampled_from(['pending', 'processed', 'error'])
)
@settings(max_examples=100)
def test_property_database_round_trip(title, url, guid, status):
    """
    Feature: environment-separation-architecture, Property 5: 数据库读写往返
    
    对于任何有效的 Article 对象，存储后再读取应得到等价数据
    """
    session = SessionLocal()
    
    # 创建并保存 Article
    original = Article(
        title=title,
        url=url,
        guid=guid,
        status=status
    )
    session.add(original)
    session.commit()
    article_id = original.id
    
    # 从数据库读取
    retrieved = session.query(Article).filter(Article.id == article_id).first()
    
    # 验证数据一致性
    assert retrieved is not None
    assert retrieved.title == title
    assert retrieved.url == url
    assert retrieved.guid == guid
    assert retrieved.status == status
    
    session.close()
```

**4. 属性 6: GUID 唯一性约束**
```python
@given(
    guid=st.text(min_size=1, max_size=512),
    title1=st.text(min_size=1, max_size=512),
    title2=st.text(min_size=1, max_size=512)
)
@settings(max_examples=100)
def test_property_guid_uniqueness(guid, title1, title2):
    """
    Feature: environment-separation-architecture, Property 6: GUID 唯一性约束
    
    对于任何已存在的 guid，尝试插入相同 guid 应该失败
    """
    session = SessionLocal()
    
    # 插入第一条记录
    article1 = Article(
        title=title1,
        url="url1",
        guid=guid
    )
    session.add(article1)
    session.commit()
    
    # 尝试插入相同 guid
    article2 = Article(
        title=title2,
        url="url2",
        guid=guid
    )
    session.add(article2)
    
    # 应该抛出 IntegrityError
    with pytest.raises(IntegrityError):
        session.commit()
    
    session.rollback()
    session.close()
```

### 集成测试

集成测试验证多个组件协同工作：

**1. 端到端流程测试**
```python
def test_end_to_end_article_processing():
    """
    测试完整的文章处理流程
    
    前提条件:
    - wewe-rss 服务正在运行
    - 数据库已初始化
    - Ollama 服务可访问
    
    流程:
    1. 从 wewe-rss 获取文章
    2. 清洗 HTML 内容
    3. LLM 分析
    4. 保存到数据库
    5. 发送通知（如果有 company_name）
    """
    # 执行一次完整的处理流程
    process_routine()
    
    # 验证数据库中有新记录
    session = SessionLocal()
    articles = session.query(Article).filter(Article.status == 'processed').all()
    assert len(articles) > 0
    
    # 验证提取的项目信息
    projects = session.query(ExtractedProject).all()
    assert len(projects) > 0
    
    session.close()
```

**2. 容器网络测试**
```python
def test_container_network_connectivity():
    """
    测试容器间网络连通性
    
    前提条件:
    - wewe-rss 已启动并完成人工登录和订阅配置
    - 用户已验证 wewe-rss 能够正常抓取文章
    
    验证:
    1. analysis-ollama 可以访问 wewe-rss API
    2. analysis-ollama 可以访问 MySQL 数据库（analysis_ollama 数据库）
    3. analysis-ollama 可以访问 Ollama 服务
    """
    # 测试 wewe-rss API
    response = requests.get(f"{settings.WEWE_RSS_URL}/feeds/123")
    assert response.status_code in [200, 401]  # 401 表示需要认证，但服务可达
    
    # 测试数据库连接（连接到 analysis_ollama 数据库）
    session = SessionLocal()
    result = session.execute("SELECT 1").scalar()
    assert result == 1
    session.close()
    
    # 测试 Ollama 服务
    response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
    assert response.status_code == 200
```

### 测试环境

- **开发环境测试**: 使用 docker-compose.dev.yml 启动服务，运行单元测试和集成测试
- **预发布环境测试**: 使用 docker-compose.yml 启动服务，运行完整的端到端测试
- **CI/CD 测试**: 在 GitHub Actions 或 GitLab CI 中自动运行所有测试

### 测试覆盖率目标

- 单元测试覆盖率: ≥ 80%
- 关键路径覆盖率: 100%（RSS 采集、LLM 分析、数据库操作）
- 属性测试: 覆盖所有设计文档中定义的属性

