# Scripts 目录说明

本目录包含运维、验证和开发辅助脚本。

## 启动脚本

| 文件 | 用途 |
|------|------|
| `start-dev.sh` | Linux/Mac 启动开发环境（直接运行 Python） |
| `start-dev.ps1` | Windows 启动开发环境（直接运行 Python） |
| `start-pre.sh` | 启动预发布环境（Docker 容器） |

## 测试脚本

| 文件 | 用途 |
|------|------|
| `run_tests.sh` | Linux/Mac 运行完整测试套件 |
| `run_tests.ps1` | Windows 运行完整测试套件 |

## 数据库脚本

| 文件 | 用途 |
|------|------|
| `init_db.sql` | 数据库 DDL，手动创建表结构时使用 |
| `init_database.py` | 执行 `init_db.sql` 初始化数据库（首次部署时使用） |
| `check_database.py` | 查看数据库统计信息（文章数、处理状态分布、最近记录） |
| `verify_database_complete.py` | 详细的数据完整性验证（表结构、外键、字段完整性、JSON 格式） |

## 验证脚本

| 文件 | 用途 |
|------|------|
| `verify_complete_workflow.py` | 验证完整处理流程（RSS → HTML → LLM → DB → 通知） |
| `verify_network_connectivity.py` | 验证容器网络连通性（DNS、HTTP、MySQL），部署排障时使用 |
| `verify_notifications.py` | 查询数据库中已发送通知的项目记录，确认通知功能正常 |
| `test_notification.py` | 向企业微信群发送一条测试通知，验证 Webhook 配置是否正确 |

## 常用命令

```bash
# 开发环境启动
bash scripts/start-dev.sh

# 预发布环境启动
bash scripts/start-pre.sh

# 运行测试
bash scripts/run_tests.sh

# 检查数据库状态
python scripts/check_database.py

# 发送测试通知
python scripts/test_notification.py

# 验证容器网络（在容器内执行）
python scripts/verify_network_connectivity.py
```
