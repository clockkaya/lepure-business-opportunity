# 需求文档

## 简介

本需求旨在将 lepure-business-opportunity（CGT MI 工具）项目从当前的"Docker + 本地混合"开发模式改造为"环境分离架构"。当前架构中，wewe-rss 通过 Docker Compose 运行，而 analysis-ollama 在本地运行，这种混合模式导致开发和部署流程不顺畅，无法方便地切换开发/预发布环境，且后续打包发布困难。

改造后的架构将实现：
- wewe-rss 作为独立的基础服务持续运行，不区分环境
- analysis-ollama 支持 dev/pre 环境配置，可容器化部署，便于打包发布
- 清晰的服务依赖关系和网络通信方案

## 术语表

- **WeWe_RSS**: 微信公众号文章抓取服务，基于 NestJS + React 构建，提供 RSS/Atom 接口
- **Analysis_Ollama**: Python 应用，负责文章分析、LLM 推理和企业微信通知
- **Base_Service**: 基础服务层，指 wewe-rss 及其 MySQL 数据库
- **Application_Service**: 应用服务层，指 analysis-ollama 分析引擎
- **Dev_Environment**: 开发环境，用于本地开发和调试
- **Pre_Environment**: 预发布环境，用于上线前验证
- **Container**: Docker 容器，用于服务的隔离运行
- **Service_Discovery**: 服务发现机制，容器间通过服务名称进行通信
- **Environment_Config**: 环境配置文件，用于区分不同部署环境的参数

## 需求

### 需求 1: 基础服务独立运行

**用户故事:** 作为开发者，我希望 wewe-rss 作为独立的基础服务持续运行，这样我可以在不同的应用环境中复用同一套基础服务。

#### 验收标准

1. THE WeWe_RSS SHALL 作为独立服务运行，不依赖 analysis-ollama 的启动状态
2. THE WeWe_RSS SHALL 通过独立的 Docker Compose 配置文件启动
3. THE WeWe_RSS SHALL 暴露 MySQL 端口 3308 和 Web 端口 4000 供外部访问
4. THE WeWe_RSS SHALL 使用持久化卷存储 MySQL 数据，确保数据在容器重启后不丢失
5. WHEN WeWe_RSS 启动时，THE MySQL_Service SHALL 在 WeWe_RSS 应用启动前完成健康检查

### 需求 2: 应用服务环境配置

**用户故事:** 作为开发者，我希望 analysis-ollama 支持 dev 和 pre 环境配置，这样我可以在不同环境中使用不同的配置参数而无需修改代码。

#### 验收标准

1. THE Analysis_Ollama SHALL 支持通过环境变量区分 dev 和 pre 环境
2. THE Analysis_Ollama SHALL 从 .env.dev 文件加载开发环境配置
3. THE Analysis_Ollama SHALL 从 .env.pre 文件加载预发布环境配置
4. WHERE dev 环境，THE Analysis_Ollama SHALL 连接到 localhost:3308 的 MySQL 数据库
5. WHERE pre 环境，THE Analysis_Ollama SHALL 连接到容器网络中的 MySQL 服务
6. THE Analysis_Ollama SHALL 在配置文件中明确定义 WEWE_RSS_URL、DB_HOST、DB_PORT、OLLAMA_BASE_URL、WECOM_WEBHOOK_URL 等关键参数
7. IF 必需的环境变量未配置，THEN THE Analysis_Ollama SHALL 在启动时输出清晰的错误信息并退出

### 需求 3: 应用服务容器化

**用户故事:** 作为运维人员，我希望 analysis-ollama 可以容器化部署，这样我可以方便地打包、分发和部署应用。

#### 验收标准

1. THE Analysis_Ollama SHALL 提供 Dockerfile 用于构建容器镜像
2. THE Analysis_Ollama_Dockerfile SHALL 基于 Python 3.10+ 官方镜像
3. THE Analysis_Ollama_Dockerfile SHALL 安装 requirements.txt 中定义的所有依赖
4. THE Analysis_Ollama_Dockerfile SHALL 设置 Asia/Shanghai 时区
5. THE Analysis_Ollama_Container SHALL 通过环境变量接收配置参数
6. WHEN Analysis_Ollama 在容器中运行时，THE Application SHALL 能够正常访问 WeWe_RSS API、MySQL 数据库和 Ollama 服务
7. THE Analysis_Ollama SHALL 提供 docker-compose.yml（或 docker-compose.pre.yml）用于生产/预发布环境部署
8. THE Analysis_Ollama SHALL 提供 docker-compose.dev.yml 用于开发环境部署（可选）
9. WHERE docker-compose.dev.yml，THE Configuration SHALL 挂载本地代码目录以便于调试
10. WHERE docker-compose.yml/docker-compose.pre.yml，THE Configuration SHALL 使用构建的镜像模拟生产环境
11. THE Analysis_Ollama_Docker_Compose SHALL 使用 external network 连接到 WeWe_RSS 创建的 Docker 网络
12. THE Analysis_Ollama_Docker_Compose SHALL 引用 wewe-rss 项目创建的网络名称（如 wewe-rss_default 或 wewe-rss_wewe-rss）

### 需求 4: 服务网络通信

**用户故事:** 作为系统架构师，我希望明确定义服务间的网络通信方案，这样可以确保在不同部署模式下服务都能正常通信。

#### 验收标准

1. WHERE dev 环境，THE Analysis_Ollama SHALL 通过 host.docker.internal 或 localhost 访问宿主机上的 WeWe_RSS 服务
2. WHERE pre 环境，THE Analysis_Ollama SHALL 通过 Docker 网络中的服务名称访问 WeWe_RSS 服务
3. THE Analysis_Ollama SHALL 能够访问外部网络中的 Ollama 服务（192.168.10.43:11434）
4. THE Analysis_Ollama SHALL 能够访问外部网络中的企业微信 Webhook API
5. WHERE Analysis_Ollama 在容器中运行，THE Container SHALL 加入与 WeWe_RSS 相同的 Docker 网络
6. THE Docker_Network SHALL 使用 bridge 模式，允许容器间通过服务名称进行 DNS 解析

### 需求 5: 环境切换机制

**用户故事:** 作为开发者，我希望能够方便地在 dev 和 pre 环境之间切换，这样我可以在本地调试后快速验证预发布环境。

#### 验收标准

1. THE System SHALL 提供 docker-compose.dev.yml 用于启动开发环境
2. THE System SHALL 提供 docker-compose.yml 或 docker-compose.pre.yml 用于启动预发布环境
3. WHERE docker-compose.dev.yml，THE Analysis_Ollama SHALL 挂载本地代码目录，方便开发调试
4. WHERE docker-compose.yml/docker-compose.pre.yml，THE Analysis_Ollama SHALL 使用构建的镜像，模拟生产环境
5. THE docker-compose.dev.yml SHALL 配置 volumes 挂载本地代码目录到容器
6. THE docker-compose.yml/docker-compose.pre.yml SHALL 不挂载代码目录，使用镜像内置代码
7. THE System SHALL 提供启动脚本或文档说明，指导用户如何切换环境
8. WHEN 切换环境时，THE User SHALL 只需更改环境变量或 Docker Compose 配置文件，无需修改应用代码
9. THE System SHALL 在文档中明确说明 dev 和 pre 环境的 docker-compose 文件差异

### 需求 6: 配置文件管理

**用户故事:** 作为开发者，我希望配置文件管理清晰且安全，这样可以避免敏感信息泄露并方便团队协作。

#### 验收标准

1. THE System SHALL 提供 .env.example 文件作为配置模板
2. THE System SHALL 在 .gitignore 中排除 .env、.env.dev、.env.pre 文件
3. THE System SHALL 在文档中说明每个配置项的含义和示例值
4. THE System SHALL 区分敏感配置（如密码、Webhook URL）和非敏感配置（如端口号）
5. WHERE 敏感配置，THE Documentation SHALL 提示用户从安全渠道获取实际值
6. THE System SHALL 为每个环境提供独立的配置文件示例（.env.dev.example、.env.pre.example）

### 需求 7: 数据库连接管理

**用户故事:** 作为开发者，我希望 analysis-ollama 能够在不同环境下正确连接数据库，这样可以确保数据访问的稳定性。

#### 验收标准

1. WHERE dev 环境，THE Analysis_Ollama SHALL 连接到 127.0.0.1:3308 的 MySQL 数据库
2. WHERE pre 环境，THE Analysis_Ollama SHALL 连接到 Docker 网络中名为 db 的 MySQL 服务
3. THE Analysis_Ollama SHALL 使用连接池管理数据库连接
4. THE Analysis_Ollama SHALL 配置合理的连接超时参数（connect_timeout、pool_timeout、socket_timeout）
5. IF 数据库连接失败，THEN THE Analysis_Ollama SHALL 记录详细的错误日志并进行重试
6. THE Analysis_Ollama SHALL 在应用启动时验证数据库连接的可用性

### 需求 8: 服务依赖声明和启动顺序

**用户故事:** 作为运维人员，我希望明确声明服务间的依赖关系和启动顺序，这样可以确保服务按正确的顺序启动并正常通信。

#### 验收标准

1. THE System SHALL 要求先启动 wewe-rss（通过 docker-compose up），再启动 analysis-ollama
2. WHEN wewe-rss 启动后，THE User SHALL 人工登录微信读书并订阅公众号
3. WHEN wewe-rss 完成初始化和订阅配置后，THE User SHALL 启动 analysis-ollama
4. THE Analysis_Ollama_Docker_Compose SHALL 使用 external network 连接到 wewe-rss 的 Docker 网络
5. THE Analysis_Ollama_Docker_Compose SHALL 配置 networks 部分，引用 wewe-rss 创建的网络为 external
6. WHERE pre 环境，THE Analysis_Ollama_Container SHALL 通过 Docker 网络中的服务名称访问 wewe-rss
7. THE Analysis_Ollama_Container SHALL 在启动时检查 wewe-rss 的可访问性
8. IF WeWe_RSS 未就绪，THEN THE Analysis_Ollama SHALL 等待重试或输出明确的错误信息
9. THE Analysis_Ollama SHALL 实现健康检查机制，验证与 wewe-rss API 的连通性
10. THE System SHALL 在文档中明确说明完整的启动流程：启动 wewe-rss → 人工登录订阅 → 启动 analysis-ollama

### 需求 9: 日志和监控

**用户故事:** 作为运维人员，我希望能够查看服务的运行日志，这样可以快速定位和解决问题。

#### 验收标准

1. THE Analysis_Ollama SHALL 输出结构化日志到标准输出
2. THE Analysis_Ollama SHALL 记录关键操作的时间戳、状态和结果
3. WHERE 容器化部署，THE Container_Logs SHALL 可通过 docker logs 命令查看
4. THE Analysis_Ollama SHALL 记录与外部服务（WeWe_RSS、Ollama、企业微信）的交互日志
5. IF 发生异常，THEN THE Analysis_Ollama SHALL 记录完整的错误堆栈信息
6. THE System SHALL 配置日志轮转策略，防止日志文件过大

### 需求 10: 文档和部署指南

**用户故事:** 作为新加入的开发者，我希望有清晰的文档和部署指南，这样可以快速理解架构并完成环境搭建。

#### 验收标准

1. THE System SHALL 提供架构说明文档，描述服务间的关系和通信方式
2. THE System SHALL 提供完整的启动流程文档，包含以下步骤：
   - 步骤 1: 启动 wewe-rss（docker-compose up -d）
   - 步骤 2: 访问 wewe-rss Web 界面，人工登录微信读书
   - 步骤 3: 在 wewe-rss 中订阅目标公众号
   - 步骤 4: 验证 wewe-rss 是否正常抓取文章
   - 步骤 5: 启动 analysis-ollama（docker-compose up -d）
3. THE System SHALL 提供开发环境搭建指南，包含详细的步骤和命令
4. THE System SHALL 提供预发布环境部署指南，包含 Docker 镜像构建和启动流程
5. THE Documentation SHALL 明确说明 analysis-ollama 的 docker-compose 需要连接到 wewe-rss 的 Docker 网络
6. THE Documentation SHALL 提供网络配置示例，展示如何使用 external network
7. THE Documentation SHALL 说明如何查看 wewe-rss 创建的 Docker 网络名称（docker network ls）
8. THE System SHALL 提供故障排查指南，列出常见问题和解决方案
9. THE Documentation SHALL 包含配置项说明，解释每个环境变量的作用
10. THE Documentation SHALL 包含网络拓扑图，展示服务间的连接关系
11. THE Documentation SHALL 说明如何验证环境是否正确配置
12. THE Documentation SHALL 说明如果先启动 analysis-ollama 会导致的问题和解决方法

### 需求 11: 数据模型和 DDL 管理

**用户故事:** 作为数据库管理员，我希望有清晰的数据库表结构定义和初始化脚本，这样可以在新环境中快速创建数据库并进行数据迁移。

#### 验收标准

1. THE System SHALL 提供 MySQL DDL 脚本，定义 articles 和 extracted_projects 表结构
2. THE DDL_Script SHALL 包含表的字段定义、数据类型、约束条件和索引
3. THE DDL_Script SHALL 使用 utf8mb4 字符集和 utf8mb4_unicode_ci 排序规则
4. THE articles 表 SHALL 包含 id、title、url、guid、published_at、fetched_at、status、summary 字段
5. THE extracted_projects 表 SHALL 包含 id、article_id、company_name、province、city、client_type、application_scene、project_name、project_stage、raw_json、created_at 字段
6. THE guid 字段 SHALL 设置唯一索引，防止重复抓取同一文章
7. THE System SHALL 提供数据库迁移脚本或工具，支持从旧版本升级到新版本
8. THE Analysis_Ollama SHALL 在启动时自动创建数据库和表结构，如果它们不存在
9. THE System SHALL 提供数据库备份和恢复指南
10. FOR ALL valid Article objects, WHEN parsed and stored, THEN re-reading from database SHALL produce equivalent data (round-trip property)

### 需求 12: 代码结构规范

**用户故事:** 作为开发者，我希望 analysis-ollama 的代码结构清晰规范，这样可以提高代码可读性和可维护性。

#### 验收标准

1. THE Analysis_Ollama SHALL 遵循 Python 项目标准目录结构
2. THE config 模块 SHALL 负责配置管理，使用 pydantic-settings 进行类型验证
3. THE core 模块 SHALL 包含业务逻辑，分为 db_repo、models、rss_collector、html_parser、llm_analyzer、notification 子模块
4. THE db_repo 模块 SHALL 提供数据库连接池管理和健康检查功能
5. THE db_repo 模块 SHALL 实现连接重试机制，最多重试 3 次，每次间隔 5 秒
6. IF 数据库连接失败超过重试次数，THEN THE Analysis_Ollama SHALL 记录错误并优雅退出
7. THE models 模块 SHALL 使用 SQLAlchemy ORM 定义数据模型
8. THE rss_collector 模块 SHALL 负责从 WeWe_RSS 获取文章列表
9. THE html_parser 模块 SHALL 负责清洗 HTML 内容，提取纯文本
10. THE llm_analyzer 模块 SHALL 负责调用 Ollama LLM 进行信息提取
11. THE notification 模块 SHALL 负责发送企业微信通知
12. THE main.py SHALL 作为应用入口，使用 schedule 库实现定时任务调度
13. THE System SHALL 使用结构化日志，包含时间戳、日志级别、模块名称和消息内容
14. THE System SHALL 支持通过环境变量配置日志级别 (DEBUG、INFO、WARNING、ERROR)
15. THE System SHALL 为每个模块提供清晰的函数文档字符串，说明参数和返回值

### 需求 13: 依赖管理和版本控制

**用户故事:** 作为开发者，我希望明确管理项目依赖和版本，这样可以确保在不同环境中使用一致的依赖版本，避免兼容性问题。

#### 验收标准

1. THE System SHALL 提供 requirements.txt 文件，列出所有 Python 依赖及其版本号
2. THE requirements.txt SHALL 包含 requests、beautifulsoup4、pymysql、SQLAlchemy、pydantic、pydantic-settings、python-dotenv、schedule 等依赖
3. THE System SHALL 为每个依赖指定明确的版本号或版本范围，避免使用不固定的版本
4. THE System SHALL 区分生产依赖和开发依赖 (可选: 使用 requirements-dev.txt)
5. THE System SHALL 提供 Python 版本要求说明 (推荐 Python 3.10+)
6. THE Dockerfile SHALL 使用固定的 Python 基础镜像版本标签，避免使用 latest 标签
7. THE System SHALL 在文档中说明如何创建虚拟环境和安装依赖
8. THE System SHALL 提供依赖更新指南，说明如何安全地升级依赖版本
9. WHERE 使用 poetry 或 pipenv，THE System SHALL 提供相应的配置文件 (pyproject.toml 或 Pipfile)
10. THE System SHALL 在 .gitignore 中排除虚拟环境目录 (venv、.venv、env)
