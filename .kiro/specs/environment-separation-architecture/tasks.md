# 任务列表

## 1. 项目结构和配置文件

- [x] 1.1 创建 analysis-ollama 目录结构
  - [x] 1.1.1 创建 scripts/ 目录
  - [x] 1.1.2 创建 docs/ 目录
  - [x] 1.1.3 创建 tests/ 目录
- [x] 1.2 创建环境配置文件
  - [x] 1.2.1 创建 .env.example
  - [x] 1.2.2 创建 .env.dev.example
  - [x] 1.2.3 创建 .env.pre.example
- [x] 1.3 更新 .gitignore
  - [x] 1.3.1 添加 .env、.env.dev、.env.pre
  - [x] 1.3.2 添加虚拟环境目录（venv、.venv、env）

## 2. 数据库 DDL 和初始化脚本

- [x] 2.1 创建 DDL 脚本
  - [x] 2.1.1 创建 scripts/init_db.sql
  - [x] 2.1.2 添加 articles 表定义（包含 feed_id 字段）
  - [x] 2.1.3 添加 extracted_projects 表定义
  - [x] 2.1.4 添加 feed_configs 表定义（未来扩展）
- [x] 2.2 更新 core/models.py
  - [x] 2.2.1 在 Article 模型中添加 feed_id 字段
  - [x] 2.2.2 创建 FeedConfig 模型（注释标记为未来扩展）

## 3. 配置管理改进

- [x] 3.1 更新 config/settings.py
  - [x] 3.1.1 添加 LOG_LEVEL 配置项
  - [x] 3.1.2 设置 DB_NAME 默认值为 "analysis_ollama"
  - [x] 3.1.3 添加配置验证逻辑
  - [x] 3.1.4 添加缺失配置的错误提示
- [x] 3.2 添加 pydantic-settings 依赖到 requirements.txt

## 4. 数据库连接改进

- [x] 4.1 更新 core/db_repo.py
  - [x] 4.1.1 实现连接重试机制（最多 3 次，间隔 5 秒）
  - [x] 4.1.2 添加详细的错误日志
  - [x] 4.1.3 实现 check_db_health() 函数
  - [x] 4.1.4 配置连接池参数（pool_size、max_overflow、pool_recycle、pool_pre_ping）
  - [x] 4.1.5 修改数据库名称为 analysis_ollama

## 5. 日志系统改进

- [x] 5.1 创建 core/logger.py
  - [x] 5.1.1 配置结构化日志格式（JSON）
  - [x] 5.1.2 包含时间戳、日志级别、模块名称、消息内容
  - [x] 5.1.3 支持通过环境变量配置日志级别
- [x] 5.2 更新所有模块使用新的日志系统
  - [x] 5.2.1 更新 main.py
  - [x] 5.2.2 更新 core/rss_collector.py
  - [x] 5.2.3 更新 core/html_parser.py
  - [x] 5.2.4 更新 core/llm_analyzer.py
  - [x] 5.2.5 更新 core/notification.py
  - [x] 5.2.6 更新 core/db_repo.py

## 6. 容器化配置

- [x] 6.1 创建 Dockerfile
  - [x] 6.1.1 基于 Python 3.10 官方镜像（固定版本标签）
  - [x] 6.1.2 设置工作目录 /app
  - [x] 6.1.3 设置时区为 Asia/Shanghai
  - [x] 6.1.4 复制 requirements.txt 并安装依赖
  - [x] 6.1.5 复制应用代码
  - [x] 6.1.6 设置 CMD 启动命令
  - [x] 6.1.7 添加健康检查配置
- [x] 6.2 创建 docker-compose.dev.yml（开发环境）
  - [x] 6.2.1 配置服务名称 analysis-ollama
  - [x] 6.2.2 使用 build 构建镜像
  - [x] 6.2.3 挂载本地代码目录（volumes）
  - [x] 6.2.4 配置环境变量文件（.env.dev）
  - [x] 6.2.5 配置 external network（wewe-rss_default）
  - [x] 6.2.6 添加 restart: unless-stopped
- [x] 6.3 创建 docker-compose.yml（预发布环境）
  - [x] 6.3.1 配置服务名称 analysis-ollama
  - [x] 6.3.2 使用 image 指定镜像
  - [x] 6.3.3 不挂载代码目录
  - [x] 6.3.4 配置环境变量文件（.env.pre）
  - [x] 6.3.5 配置 external network（wewe-rss_default）
  - [x] 6.3.6 添加 restart: unless-stopped

## 7. 依赖管理

- [x] 7.1 更新 requirements.txt
  - [x] 7.1.1 固定所有依赖版本号
  - [x] 7.1.2 添加 pydantic-settings
  - [x] 7.1.3 添加 python-json-logger（用于结构化日志）
  - [x] 7.1.4 验证所有依赖兼容性

## 8. 错误处理改进

- [x] 8.1 更新 core/rss_collector.py
  - [x] 8.1.1 添加网络错误处理
  - [x] 8.1.2 添加超时配置（30 秒）
  - [x] 8.1.3 添加详细的错误日志
- [x] 8.2 更新 core/llm_analyzer.py
  - [x] 8.2.1 添加超时配置（120 秒）
  - [x] 8.2.2 添加 JSON 解析错误处理
  - [x] 8.2.3 失败时返回 None（不抛出异常）
- [x] 8.3 更新 core/notification.py
  - [x] 8.3.1 添加网络错误处理
  - [x] 8.3.2 添加超时配置（10 秒）
  - [x] 8.3.3 失败时记录日志但不影响主流程
- [x] 8.4 更新 main.py
  - [x] 8.4.1 添加全局异常捕获
  - [x] 8.4.2 添加事务回滚逻辑
  - [x] 8.4.3 确保异常不会导致应用退出

## 9. 启动时健康检查

- [x] 9.1 创建 core/health_check.py
  - [x] 9.1.1 实现配置验证函数
  - [x] 9.1.2 实现数据库连接检查函数
  - [x] 9.1.3 实现 WeWe-RSS 连通性检查函数（可选）
- [x] 9.2 更新 main.py
  - [x] 9.2.1 在启动时调用健康检查
  - [x] 9.2.2 如果检查失败，输出错误并退出

## 10. 文档

- [x] 10.1 创建 docs/ARCHITECTURE.md
  - [x] 10.1.1 描述整体架构
  - [x] 10.1.2 描述服务间通信方式
  - [x] 10.1.3 包含网络拓扑图（Mermaid）
  - [x] 10.1.4 说明扩展性设计（多公众号、多 webhook）
- [x] 10.2 创建 docs/DEPLOYMENT.md
  - [x] 10.2.1 开发环境搭建指南
  - [x] 10.2.2 预发布环境部署指南
  - [x] 10.2.3 完整的启动流程（包含人工等待步骤）
  - [x] 10.2.4 配置项说明
  - [x] 10.2.5 故障排查指南
  - [x] 10.2.6 如何查看 Docker 网络名称
  - [x] 10.2.7 环境验证方法
- [x] 10.3 更新 analysis-ollama/README.md
  - [x] 10.3.1 项目简介
  - [x] 10.3.2 快速开始
  - [x] 10.3.3 配置说明
  - [x] 10.3.4 链接到详细文档

## 11. 测试

- [x] 11.1 创建测试目录结构
  - [x] 11.1.1 创建 tests/unit/ 目录
  - [x] 11.1.2 创建 tests/integration/ 目录
  - [x] 11.1.3 创建 tests/property/ 目录
  - [x] 11.1.4 创建 tests/conftest.py（pytest 配置）
- [x] 11.2 编写单元测试
  - [x] 11.2.1 tests/unit/test_config.py（配置管理测试）
  - [x] 11.2.2 tests/unit/test_db_repo.py（数据库连接测试）
  - [x] 11.2.3 tests/unit/test_html_parser.py（HTML 解析测试）
  - [x] 11.2.4 tests/unit/test_models.py（数据模型测试）
- [x] 11.3 编写属性测试
  - [x] 11.3.1 tests/property/test_config_driven.py（属性 1）
  - [x] 11.3.2 tests/property/test_structured_logging.py（属性 3）
  - [x] 11.3.3 tests/property/test_database_round_trip.py（属性 5）
  - [x] 11.3.4 tests/property/test_guid_uniqueness.py（属性 6）
- [ ] 11.4 编写集成测试
  - [x] 11.4.1 tests/integration/test_end_to_end.py（端到端流程测试）
  - [x] 11.4.2 tests/integration/test_network_connectivity.py（网络连通性测试）
- [x] 11.5 添加测试依赖
  - [x] 11.5.1 创建 requirements-dev.txt
  - [x] 11.5.2 添加 pytest
  - [x] 11.5.3 添加 hypothesis
  - [x] 11.5.4 添加 pytest-cov
  - [x] 11.5.5 添加 pytest-mock

## 12. 扩展性准备（可选）

- [x] 12.1 添加 feed_configs 表支持
  - [x] 12.1.1 在 DDL 中添加表定义
  - [x] 12.1.2 在 models.py 中添加 ORM 模型
  - [x] 12.1.3 添加注释说明这是未来扩展功能
- [x] 12.2 预留多 feed 采集接口
  - [x] 12.2.1 在 rss_collector.py 中添加 fetch_multiple_feeds() 函数（注释）
  - [x] 12.2.2 在 notification.py 中添加动态 webhook 路由逻辑（注释）

## 13. 验证和测试

- [x] 13.1 本地开发环境验证
  - [x] 13.1.1 启动 wewe-rss
  - [x] 13.1.2 人工登录并订阅公众号
  - [x] 13.1.3 验证 wewe-rss 正常抓取文章
  - [x] 13.1.4 启动 analysis-ollama（dev 环境）
  - [x] 13.1.5 验证文章处理流程正常
  - [x] 13.1.6 验证数据库记录正确
  - [x] 13.1.7 验证企业微信通知发送成功
- [x] 13.2 预发布环境验证
  - [x] 13.2.1 构建 analysis-ollama 镜像
  - [x] 13.2.2 启动 analysis-ollama（pre 环境）
  - [x] 13.2.3 验证容器网络连通性
  - [x] 13.2.4 验证完整流程正常
- [x] 13.3 运行测试套件
  - [x] 13.3.1 运行单元测试
  - [x] 13.3.2 运行属性测试
  - [x] 13.3.3 运行集成测试
  - [x] 13.3.4 生成测试覆盖率报告

## 14. 清理和优化

- [x] 14.1 代码审查
  - [x] 14.1.1 检查所有模块的文档字符串
  - [x] 14.1.2 检查代码风格一致性
  - [x] 14.1.3 移除未使用的导入和代码
- [x] 14.2 性能优化
  - [x] 14.2.1 验证数据库连接池配置合理
  - [x] 14.2.2 验证 HTTP 请求超时配置合理
- [x] 14.3 安全检查
  - [x] 14.3.1 确认敏感信息不在代码中
  - [x] 14.3.2 确认 .env 文件在 .gitignore 中
  - [x] 14.3.3 确认 Docker 镜像不包含敏感信息

