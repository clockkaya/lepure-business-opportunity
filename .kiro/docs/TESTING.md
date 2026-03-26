# 测试指南

## 快速开始

### 1. 安装测试依赖

```bash
# 激活虚拟环境
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
# 或
source .venv/bin/activate      # Linux/Mac

# 安装测试依赖
pip install -r requirements-dev.txt
```

### 2. 运行测试

#### 使用测试脚本（推荐）

```bash
# Windows
.\scripts\run_tests.ps1

# Linux/Mac
./scripts/run_tests.sh
```

#### 手动运行

```bash
# 运行所有单元测试
pytest tests/unit/ -v

# 运行所有属性测试
pytest tests/property/ -v

# 运行特定测试文件
pytest tests/unit/test_config.py -v

# 运行特定测试函数
pytest tests/unit/test_config.py::test_settings_with_all_required_fields -v
```

### 3. 生成覆盖率报告

```bash
# 生成 HTML 覆盖率报告
pytest tests/unit/ tests/property/ --cov=. --cov-report=html --cov-report=term

# 查看报告
# 打开 htmlcov/index.html
```

## 测试类型

### 单元测试 (Unit Tests)

测试单个组件的功能，不依赖外部服务。

```bash
pytest tests/unit/ -v
```

**测试文件**:
- `test_config.py` - 配置管理
- `test_html_parser.py` - HTML 解析
- `test_models.py` - 数据模型
- `test_db_utils.py` - 数据库工具

### 属性测试 (Property-Based Tests)

使用 Hypothesis 生成大量随机输入，验证系统属性。

```bash
pytest tests/property/ -v
```

**测试文件**:
- `test_config_driven.py` - 配置驱动行为
- `test_structured_logging.py` - 结构化日志
- `test_database_round_trip.py` - 数据库往返
- `test_guid_uniqueness.py` - GUID 唯一性

### 集成测试 (Integration Tests)

测试多个组件协同工作，需要外部服务。

```bash
pytest tests/integration/ -v -m integration
```

**注意**: 集成测试需要以下服务运行：
- MySQL 数据库
- WeWe-RSS 服务
- Ollama 服务（可选）

## 测试标记

使用 pytest markers 过滤测试：

```bash
# 只运行集成测试
pytest -m integration

# 排除慢速测试
pytest -m "not slow"

# 运行单元测试和属性测试
pytest -m "unit or property"
```

## 常见问题

### Q: 测试失败怎么办？

A: 查看错误消息和堆栈跟踪：
```bash
pytest tests/unit/test_config.py -v -s
```

### Q: 如何跳过集成测试？

A: 集成测试默认会跳过（如果外部服务不可用）。如果要明确跳过：
```bash
pytest tests/unit/ tests/property/ -v
```

### Q: 如何查看测试覆盖率？

A: 运行带覆盖率的测试：
```bash
pytest --cov=. --cov-report=html
# 打开 htmlcov/index.html
```

### Q: 属性测试运行很慢？

A: 属性测试默认运行 100 次迭代。可以减少迭代次数（仅用于开发）：
```python
@settings(max_examples=10)  # 减少到 10 次
```

## 开发工作流

### 1. 编写新功能

```bash
# 1. 编写测试
# 2. 运行测试（应该失败）
pytest tests/unit/test_new_feature.py -v

# 3. 实现功能
# 4. 再次运行测试（应该通过）
pytest tests/unit/test_new_feature.py -v
```

### 2. 修复 Bug

```bash
# 1. 编写重现 bug 的测试
# 2. 运行测试（应该失败）
pytest tests/unit/test_bug_fix.py -v

# 3. 修复 bug
# 4. 再次运行测试（应该通过）
pytest tests/unit/test_bug_fix.py -v
```

### 3. 重构代码

```bash
# 1. 运行所有测试（应该通过）
pytest tests/unit/ -v

# 2. 重构代码
# 3. 再次运行所有测试（应该仍然通过）
pytest tests/unit/ -v
```

## CI/CD 集成

### GitHub Actions 示例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run tests
        run: |
          pytest tests/unit/ tests/property/ -v --cov
```

## 参考资料

- [Pytest 文档](https://docs.pytest.org/)
- [Hypothesis 文档](https://hypothesis.readthedocs.io/)
- [测试 README](tests/README.md)
- [测试总结](tests/TEST_SUMMARY.md)
