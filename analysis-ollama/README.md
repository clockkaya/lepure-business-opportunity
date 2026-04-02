# Analysis-Ollama

基于 Ollama 本地 LLM 的 CGT（细胞与基因治疗）行业情报分析服务。

---

## 概述

Analysis-Ollama 是一个 Python 服务，自动从 wewe-rss 采集微信公众号文章，通过 LLM 提取结构化商业情报，并推送通知至企业微信群。

### 核心功能

- **自动采集**：定时从 wewe-rss RSS Feed 拉取新文章
- **智能分析**：调用 Ollama LLM 提取结构化信息（公司、项目、阶段等）
- **智能通知**：将格式化情报报告推送至企业微信群
- **环境分离**：支持 Dev（本地调试）和 Pre（生产部署）两套环境
- **容器化部署**：Pre 环境基于 Docker，便于分发
- **结构化日志**：JSON 格式日志，便于监控
- **健康检查**：启动时自动验证所有依赖项

---

## 快速开始

### 前置条件

- Python 3.10+（Dev 环境）
- Docker & Docker Compose（Pre 环境）
- wewe-rss 服务已运行
- Ollama LLM 服务可访问
- 企业微信 Webhook URL（可选）

### 开发环境（Dev）

Dev 环境直接运行 Python，不使用 Docker，方便开发调试。

```bash
# 1. 克隆仓库
git clone <repository-url>
cd analysis-ollama

# 2. 创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac
pip install -r requirements.txt

# 3. 编辑 .env.dev，填入实际配置值

# 4. 启动服务
$env:ENV="dev"; python -m app.main          # Windows PowerShell
# ENV=dev python -m app.main               # Linux/Mac

# 或使用启动脚本
powershell scripts/start-dev.ps1           # Windows
# bash scripts/start-dev.sh               # Linux/Mac
```

### 预发布/生产环境（Pre）

Pre 环境使用 Docker 容器运行。在根目录下使用一体化 `docker-compose.yml` 启动。

```bash
# 1. 在根目录配置 .env.pre（由 analysis-ollama/.env.example 复制而来）

# 2. 启动服务（在根目录）
docker-compose up -d agent

# 3. 查看日志
docker-compose logs -f agent
```

---

## 配置说明

### 环境文件

应用根据 `ENV` 环境变量自动加载对应配置文件：

- **`.env.dev`**：本地 Python 直接运行
  - 数据库：`127.0.0.1:3308`（宿主机端口映射）
  - WeWe-RSS：`http://localhost:4000`

- **`.env.pre`**：Docker 容器运行
  - 数据库：`db:3306`（Docker 网络内部）
  - WeWe-RSS：`http://app:4000`

### 环境对比

| 配置项 | Dev 环境 | Pre 环境 | 说明 |
|--------|----------|----------|------|
| 运行方式 | Python 直接运行 | Docker 容器 | Dev 方便调试，Pre 用于生产 |
| `ENV` | `dev` | `pre` | 环境标识 |
| `WEWE_RSS_URL` | `http://localhost:4000` | `http://app:4000` | Dev 访问宿主机，Pre 访问容器 |
| `DB_HOST` | `127.0.0.1` | `db` | Dev 访问宿主机，Pre 访问容器 |
| `DB_PORT` | `3308` | `3306` | Dev 使用映射端口，Pre 使用容器端口 |

### 必填环境变量

| 变量名 | 说明 | Dev 示例 | Pre 示例 |
|--------|------|----------|----------|
| `ENV` | 环境标识 | `dev` | `pre` |
| `WEWE_RSS_URL` | WeWe-RSS API 地址 | `http://localhost:4000` | `http://app:4000` |
| `AUTH_CODE` | WeWe-RSS 认证码 | `your_auth_code` | `your_auth_code` |
| `DB_HOST` | MySQL 主机 | `127.0.0.1` | `db` |
| `DB_PORT` | MySQL 端口 | `3308` | `3306` |
| `DB_USER` | MySQL 用户名 | `root` | `root` |
| `DB_PASSWORD` | MySQL 密码 | `your_password` | `your_password` |
| `DB_NAME` | 数据库名 | `analysis_ollama` | `analysis_ollama` |
| `OLLAMA_BASE_URL` | Ollama API 地址 | `http://192.168.10.43:11434` | `http://192.168.10.43:11434` |
| `MODEL_NAME` | LLM 模型名称 | `deepseek-r1:32b` | `deepseek-r1:32b` |
| `WECOM_WEBHOOK_URL` | 企业微信 Webhook（可选） | `` | `` |

### 可选环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `POLL_INTERVAL_MINUTES` | 轮询间隔（分钟） | `60` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

---

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        外部服务                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Ollama     │  │  企业微信    │  │  微信读书    │      │
│  │ 192.168.10.43│  │   Webhook    │  │   平台       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────┼───────────────────────────────┐
│                      应用服务层                              │
│  ┌──────────────────────────┴────────────────────────────┐  │
│  │          analysis-ollama (Python 应用)                │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │  │
│  │  │ RSS 服务   │  │ LLM 服务   │  │  通知服务  │     │  │
│  │  └────────────┘  └────────────┘  └────────────┘     │  │
│  │  ┌────────────┐  ┌────────────┐                      │  │
│  │  │  数据仓储  │  │  文章处理  │                      │  │
│  │  └────────────┘  └────────────┘                      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ Docker 网络 (lepure-business-opportunity_default)
┌─────────────────────────────┼───────────────────────────────┐
│                      基础服务层                              │
│  ┌──────────────────────────┴────────────────────────────┐  │
│  │              wewe-rss (NestJS + React)                │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │  │
│  │  │  Web UI    │  │  API       │  │  定时任务  │     │  │
│  │  │  :4000     │  │  /feeds    │  │  (Cron)    │     │  │
│  │  └────────────┘  └────────────┘  └────────────┘     │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              MySQL 8.0 数据库                         │  │
│  │              端口：3308（宿主机）/ 3306（容器内）      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 分层架构

| 层级 | 目录 | 职责 |
|------|------|------|
| 配置层 | `app/core/settings.py` | 环境变量管理与验证 |
| 数据模型层 | `app/models/` | SQLModel ORM 模型定义 |
| 业务逻辑层 | `app/services/` | RSS 采集、LLM 分析、通知发送 |
| 协调层 | `app/services/processor.py` | 文章处理编排 |
| 工具层 | `app/utils/` | 日志、HTML 解析、数据库连接池、健康检查 |

---

## 项目结构

```
analysis-ollama/
├── app/                          # 应用核心代码
│   ├── main.py                   # 程序入口
│   ├── core/
│   │   ├── settings.py           # 统一配置中心
│   │   ├── database.py           # 数据库引擎与 Session
│   │   ├── logging.py            # 结构化日志配置
│   │   └── health_checker.py     # 依赖项健康检查
│   ├── models/
│   │   ├── article.py            # 文章表模型
│   │   └── project.py            # 提取项目模型
│   ├── services/
│   │   ├── rss_fetcher.py        # RSS 抓取服务
│   │   ├── llm_analyzer.py       # LLM 核心分析服务
│   │   ├── wecom_notifier.py     # 企业微信通知服务
│   │   └── processor.py          # 业务流程控制器
│   └── utils/
│       └── html_cleaner.py       # HTML 正文清洗
├── tests/                        # 完整测试套件
│   ├── unit/                     # 单元测试
│   ├── property/                 # 基于属性的测试
│   └── integration/              # 集成测试
├── scripts/                      # 运维与开发工具脚本
├── .env.example                  # 环境变量模板
├── Dockerfile                    # 生产镜像构建文件
├── docker-compose.yml            # 本地容器运行配置
├── requirements.txt              # 运行依赖
└── README.md                     # 本文件
```

---

## 处理流程

1. **RSS 采集**：每 N 分钟（可配置）从 wewe-rss 拉取新文章
2. **去重**：通过 GUID 判断文章是否已处理
3. **HTML 清洗**：提取正文纯文本，过滤广告和无关内容
4. **LLM 分析**：调用 Ollama 提取结构化字段
5. **数据存储**：写入 MySQL（`analysis_articles` + `analysis_extracted_projects`）
6. **推送通知**：若提取到公司名称，发送企业微信消息

---

## 数据模型

### analysis_articles（文章表）

| 字段 | 说明 |
|------|------|
| `id` | 主键 |
| `title` | 文章标题 |
| `url` | 文章链接 |
| `guid` | RSS 唯一标识（去重依据） |
| `published_at` | 发布时间 |
| `fetched_at` | 采集时间 |
| `status` | 处理状态：`pending` / `processed` / `error` |
| `summary` | LLM 生成的摘要 |

### analysis_extracted_projects（提取项目表）

| 字段 | 说明 |
|------|------|
| `id` | 主键 |
| `article_id` | 关联文章 ID |
| `company_name` | 公司名称 |
| `province` / `city` | 省份 / 城市 |
| `client_type` | 客户类型 |
| `application_scene` | 应用场景（MSC / iPSC / AAV 等） |
| `project_name` | 项目名称 |
| `project_stage` | 项目阶段（IND / IIT / I期 等） |
| `raw_json` | LLM 原始 JSON 输出 |
| `created_at` | 创建时间 |

---

## 日志

所有日志以结构化 JSON 格式输出：

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "module": "services.rss_service",
  "message": "成功从 RSS Feed 获取 5 篇文章"
}
```

日志级别：`DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`

---

## 错误处理

| 错误类型 | 处理策略 |
|----------|----------|
| 配置错误 | 启动时输出明确错误信息并退出 |
| 数据库连接失败 | 重试 3 次（间隔 5 秒），仍失败则退出 |
| RSS 采集失败 | 记录日志，跳过本轮，等待下次轮询 |
| LLM 分析失败 | 将文章标记为 `error`，继续处理下一篇 |
| 企业微信通知失败 | 记录日志，不影响主流程 |

---

## 健康检查

启动时自动验证：
1. 配置完整性（所有必填环境变量）
2. 数据库连接
3. WeWe-RSS 连通性（可选）

Docker 健康检查每 30 秒执行一次数据库连通性验证。

---

## 开发指南

### 运行测试

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 使用脚本运行
powershell scripts/run_tests.ps1   # Windows
# bash scripts/run_tests.sh        # Linux/Mac

# 手动运行
pytest

# 带覆盖率报告
pytest --cov=. --cov-report=html
```

### 代码格式化

```bash
black .    # 格式化
flake8 .   # 代码检查
```

---

## 常见问题

**数据库连接失败**
- 确认 MySQL 服务正在运行
- 检查 `.env` 文件中的 `DB_HOST` 和 `DB_PORT`
- Dev 环境：确认 3308 端口已映射
- Pre 环境：确认容器在 `lepure-business-opportunity_default` 网络中

**WeWe-RSS 连通性检查失败**
- 确认 wewe-rss 服务已启动
- 检查 `WEWE_RSS_URL` 配置
- 确认已完成微信登录和公众号订阅

**Docker 网络不存在**
- 先启动 wewe-rss：`docker-compose up -d`（在 wewe-rss 目录）
- 查看实际网络名：`docker network ls`
