# 单元测试报告 (Unit Test Report)

**执行日期**: 2026-03-25  
**测试框架**: pytest 8.0.0  
**Python 版本**: 3.12.10

## 测试概览 (Test Overview)

- **总测试数**: 39
- **通过**: 19 (48.7%)
- **失败**: 20 (51.3%)
- **代码覆盖率**: 19%

## 测试结果详情 (Test Results by Module)

### 1. HTML Parser Tests (test_html_parser.py)
**状态**: ✅ 全部通过 (12/12)

所有 HTML 解析测试均通过，包括：
- 基本 HTML 清洗
- 空内容和 None 处理
- Script/Style/Iframe 标签移除
- 微信文章内容提取
- 段落结构保留
- HTML 实体处理
- 复杂结构和格式错误的 HTML 处理

### 2. Data Models Tests (test_models.py)
**状态**: ⚠️ 部分通过 (7/15)

**通过的测试**:
- ✅ Article 创建
- ✅ GUID 唯一性约束
- ✅ 查询不存在的 GUID
- ✅ Article 默认值
- ✅ ExtractedProject 外键约束

**失败的测试**:
- ❌ test_article_get_by_guid - UNIQUE constraint 冲突
- ❌ test_article_get_by_status - 测试隔离问题（期望 2 条记录，实际 4 条）
- ❌ test_article_update_status - UNIQUE constraint 冲突
- ❌ test_extracted_project_creation - UNIQUE constraint 冲突
- ❌ test_extracted_project_get_by_article_id - UNIQUE constraint 冲突
- ❌ test_extracted_project_default_values - UNIQUE constraint 冲突

**问题原因**: 
- 测试隔离不完善：`sample_article_data` fixture 使用相同的 GUID，导致多个测试之间数据冲突
- `test_session` fixture 的 rollback 未能正确清理数据

### 3. Configuration Tests (test_config.py)
**状态**: ❌ 全部失败 (0/7)

**失败原因**: 
- ModuleNotFoundError: No module named 'config'
- 测试使用 `from config.settings import Settings`，但应该使用 `from app.config.settings import Settings`

**受影响的测试**:
- test_settings_with_all_required_fields
- test_settings_db_name_default
- test_settings_log_level_default
- test_settings_log_level_validation
- test_settings_missing_required_field
- test_settings_database_url_property
- test_settings_whitespace_trimming

### 4. Database Utils Tests (test_db_utils.py)
**状态**: ⚠️ 部分通过 (2/9)

**通过的测试**:
- ✅ test_check_db_health_success
- ✅ test_check_db_health_failure

**失败的测试**:
- ❌ test_create_db_engine_with_sqlite - SQLite 不支持 `max_overflow` 和 `pool_timeout` 参数
- ❌ test_get_session_context_manager - ModuleNotFoundError: No module named 'utils'
- ❌ test_get_session_auto_commit - ModuleNotFoundError: No module named 'models'
- ❌ test_get_session_auto_rollback_on_error - ModuleNotFoundError: No module named 'models'
- ❌ test_get_pool_status - TypeError: 'int' object is not callable (pool.size() 应该是 pool.size)
- ❌ test_engine_pool_pre_ping - SQLite 参数不兼容
- ❌ test_engine_connection_args - SQLite 参数不兼容

**问题原因**:
1. 导入路径错误：应使用 `app.utils` 和 `app.models` 而非 `utils` 和 `models`
2. SQLite 连接池限制：`create_db_engine` 函数对 SQLite 传递了不支持的参数
3. 代码错误：`get_pool_status` 函数中 `pool.size()` 应该是 `pool.size`

## 代码覆盖率 (Code Coverage)

| 模块 | 语句数 | 未覆盖 | 覆盖率 |
|------|--------|--------|--------|
| app/models/article.py | 36 | 10 | 72% |
| app/models/project.py | 26 | 4 | 85% |
| app/utils/html_parser.py | 23 | 3 | 87% |
| app/utils/db_utils.py | 77 | 38 | 51% |
| app/main.py | 57 | 57 | 0% |
| app/services/* | 276 | 276 | 0% |
| app/utils/health_check.py | 87 | 87 | 0% |
| **总计** | **603** | **491** | **19%** |

## 主要问题总结 (Key Issues)

### 1. 导入路径问题
多个测试文件使用了错误的导入路径：
- ❌ `from config.settings import Settings`
- ❌ `from utils.db_utils import get_session`
- ❌ `from models.article import Article`

应该使用：
- ✅ `from app.config.settings import Settings`
- ✅ `from app.utils.db_utils import get_session`
- ✅ `from app.models.article import Article`

### 2. 测试隔离问题
`sample_article_data` fixture 在所有测试中使用相同的 GUID (`test-guid-123`)，导致：
- 多个测试尝试插入相同 GUID 的记录
- UNIQUE constraint 冲突
- 测试之间相互影响

**建议修复**：使用 UUID 或测试名称生成唯一的 GUID

### 3. SQLite 兼容性问题
`create_db_engine` 函数对 SQLite 传递了不支持的连接池参数：
- `max_overflow`
- `pool_timeout`

**建议修复**：检测数据库类型，仅对 MySQL 传递这些参数

### 4. 代码错误
`get_pool_status` 函数中：
```python
'pool_size': pool.size(),  # ❌ 错误：size 是属性，不是方法
```

应该改为：
```python
'pool_size': pool.size,  # ✅ 正确
```

## 建议的修复优先级 (Recommended Fix Priority)

### 高优先级 (High Priority)
1. **修复导入路径** - 影响 14 个测试
2. **修复测试隔离问题** - 影响 6 个测试
3. **修复 `get_pool_status` 代码错误** - 影响 1 个测试

### 中优先级 (Medium Priority)
4. **修复 SQLite 兼容性** - 影响 3 个测试，但不影响生产环境（生产使用 MySQL）

## 下一步行动 (Next Steps)

1. 修复所有导入路径错误
2. 改进 fixture 设计，确保测试隔离
3. 修复 `get_pool_status` 函数
4. 添加数据库类型检测，处理 SQLite 特殊情况
5. 重新运行测试，目标：100% 通过率
6. 提高代码覆盖率至 80% 以上

## 测试命令 (Test Commands)

```bash
# 运行所有单元测试
pytest tests/unit/ -v

# 运行单元测试并生成覆盖率报告
pytest tests/unit/ -v --cov=app --cov-report=term --cov-report=html

# 运行特定测试文件
pytest tests/unit/test_html_parser.py -v

# 查看 HTML 覆盖率报告
# 打开 htmlcov/index.html
```
