# lepure-business-opportunity

CGT（细胞与基因治疗）行业市场情报工具，自动采集微信公众号文章，通过本地 LLM 提取结构化商业信息，并推送至企业微信群。

---

## 项目背景

CGT 行业发展迅速，新客户与项目层出不穷。人工收集信息效率低、覆盖不全，导致销售难以精准挖掘客户项目动态。本项目通过自动化采集 + AI 提取，实现 7×24 小时行业监控，预计每位市场/销售人员每周节省 4-6 小时信息整理工时。

---

## 整体架构

本仓库包含两个子项目，协同工作：

```
lepure-business-opportunity/
├── wewe-rss/           # 微信公众号 RSS 订阅服务（NestJS + React）
└── analysis-ollama/    # 文章分析与通知服务（Python + Ollama LLM）
```

### 数据流

```
微信公众号
    │
    ▼
wewe-rss（RSS 订阅 + Web UI）
    │  HTTP API / RSS Feed
    ▼
analysis-ollama（定时采集 → LLM 分析 → 结构化存储）
    │
    ▼
MySQL 数据库（analysis_articles + analysis_extracted_projects）
    │
    ▼
企业微信群（Webhook 推送情报报告）
```

---

## 子项目说明

### wewe-rss

开源微信公众号转 RSS 工具，负责订阅公众号并提供文章 API。

- 技术栈：NestJS + React + MySQL
- 端口：4000
- 部署方式：Docker Compose

### analysis-ollama

核心分析服务，负责从 wewe-rss 拉取文章、调用本地 Ollama LLM 提取结构化信息并推送通知。

- 技术栈：Python 3.10+ + SQLAlchemy + SQLModel + Loguru
- LLM：Ollama（默认模型 `deepseek-r1:32b`，部署于 `192.168.10.43:11434`）
- 部署方式：Dev 环境直接运行 Python；Pre/生产环境使用 Docker

详细文档见 [analysis-ollama/README.md](analysis-ollama/README.md)。

---

## 快速开始

### 前置条件

- Docker & Docker Compose
- Ollama 服务（本地或局域网）
- 企业微信 Webhook URL（可选）

### 1. 启动 wewe-rss

```bash
cd wewe-rss
docker-compose up -d
```

访问 `http://localhost:4000`，完成微信登录并订阅目标公众号（如医麦客、细胞与基因治疗前沿等）。

### 2. 启动 analysis-ollama（开发环境）

```bash
cd analysis-ollama
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r requirements.txt

# 编辑 .env.dev 填入实际配置
$env:ENV="dev"; python -m app.main
```

### 3. 启动 analysis-ollama（生产环境）

```bash
cd analysis-ollama
# 编辑 .env.pre 填入实际配置
docker-compose up -d
```

---

## 核心功能

- 定时从 wewe-rss 拉取新文章（默认每 60 分钟）
- GUID 去重，避免重复处理
- HTML 清洗，提取纯文本
- 调用 Ollama LLM 提取结构化字段：公司名称、省份、城市、客户类型、应用场景、项目名称、项目阶段
- 结果写入 MySQL（`analysis_articles` + `analysis_extracted_projects`）
- 有公司名称时自动推送企业微信通知

---

## 提取字段说明

| 字段 | 说明 |
|------|------|
| `company_name` | 公司名称 |
| `province` / `city` | 省份 / 城市 |
| `client_type` | 客户类型 |
| `application_scene` | 应用场景（MSC / iPSC / AAV 等） |
| `project_name` | 项目名称 |
| `project_stage` | 项目阶段（IND / IIT / I期 等） |
| `raw_json` | LLM 原始 JSON 输出 |

---

## 开发工具脚本

位于 `analysis-ollama/scripts/`：

| 脚本 | 用途 |
|------|------|
| `init_database.py` | 初始化数据库表结构 |
| `check_database.py` | 检查数据库记录和统计 |
| `verify_database_complete.py` | 完整数据库记录验证 |
| `verify_complete_workflow.py` | 端到端工作流验证 |
| `verify_network_connectivity.py` | 网络连通性检查 |
| `verify_notifications.py` | 企业微信通知验证 |
| `start-dev.sh` / `start-dev.ps1` | 启动开发环境 |
| `run_tests.sh` / `run_tests.ps1` | 运行测试套件 |

---

## 当前分支

`feat-feasibility` — 可行性验证阶段，核心流程已跑通，正在完善测试覆盖与生产部署配置。

---

## 参考文档

- [analysis-ollama/README.md](analysis-ollama/README.md) — 详细架构、配置和部署说明
- [.todo/CGT MI 工具 PRD.md](.todo/CGT%20MI%20%E5%B7%A5%E5%85%B7%20PRD.md) — 产品需求文档
- [.todo/CGT MI 工具 SOW.md](.todo/CGT%20MI%20%E5%B7%A5%E5%85%B7%20SOW.md) — 技术可行性与工作说明
