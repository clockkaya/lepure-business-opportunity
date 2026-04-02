# lepure-business-opportunity

CGT（细胞与基因治疗）行业市场情报工具，自动采集微信公众号文章，通过本地 LLM 提取结构化商业信息，并推送至企业微信群。

---

## 项目背景

CGT 行业发展迅速，新客户与项目层出不穷。人工收集信息效率低、覆盖不全，导致销售难以精准挖掘客户项目动态。本项目通过自动化采集 + AI 提取，实现 7×24 小时行业监控，预计每位市场/销售人员每周节省 4-6 小时信息整理工时。

---

## 整体架构

本仓库采用一体化部署方案，通过根目录的 `docker-compose.yml` 协同工作：

```
lepure-business-opportunity/
├── docker-compose.yml  # 一体化部署配置文件
├── .env                # 根目录环境变量（数据库 root 密码等）
├── wewe-rss/           # 微信公众号 RSS 订阅服务
└── analysis-ollama/    # 文章分析与通知服务（Python 3.10+）
```

### 数据流

```
微信公众号
    │
    ▼
wewe-rss（订阅服务）
    │  HTTP API
    ▼
analysis-ollama（采集 → AI 分析 → 存储）
    │
    ▼
MySQL (opportunity-db)
    │
    ▼
企业微信（Webhook 通知）
```

---

## 快速开始

### 前置条件

- Docker & Docker Compose
- Ollama 服务（建议部署在独立宿主机，默认地址 `192.168.10.43:11434`）

### 1. 环境配置

复制并编辑各项目的环境变量文件：

```bash
# 根目录 (数据库配置)
cp .env.example .env

# wewe-rss (RSS 配置)
cp wewe-rss/.env.example wewe-rss/.env

# analysis-ollama (AI 与通知配置)
cp analysis-ollama/.env.example analysis-ollama/.env.pre
```

### 2. 启动服务（一体化部署）

在根目录下运行：

```bash
docker-compose up -d
```

启动顺序：`db` (MySQL) → `app` (wewe-rss) → `agent` (analysis-ollama)。

### 3. 验证

- **WeWe-RSS**: 访问 `http://localhost:4000`
- **数据库**: 宿主机通过 `localhost:3308` 访问
- **日志**: `docker-compose logs -f agent` 查看分析进度

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
