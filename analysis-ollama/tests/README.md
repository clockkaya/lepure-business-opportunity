# 测试文档

本目录包含 analysis-ollama 项目的所有测试。

## 测试结构

```
tests/
├── conftest.py              # Pytest 配置和共享 fixtures
├── unit/                    # 单元测试
│   ├── test_config.py       # 配置管理测试
│   ├── test_db_utils.py     # 数据库工具测试
│   ├── test_html_parser.py  # HTML 解析测试
│   └── test_models.py       # 数据模型测试
├── property/                # 属性测试（基于 Hypothesis）
│   ├── test_config_driven.py          # 属性 1: 配置驱动行为
│   ├── test_structured_logging.py     # 属性 3: 结构化日志
│   ├── test_database_round_trip.py    # 属性 5: 数据库往返
│   └── test_guid_uniqueness.py        # 属性 6: GUID 唯一性
└── integration/             # 集成测试
    ├── test_end_to_end.py            # 端到端流程测试
    └── test_network_connectivity.py  # 网络连通性测试
```

## 测试类型

### 单元测试 (Unit Tests)

单元测试验证单个组件的功能，不依赖外部服务。

**运行单元测试:**
```bash
pytest tests/unit/ -v
```

### 属性测试 (Property-Based Tests)

属性测试使用 Hypothesis 库生成大量随机输入，验证系统的通用属性。每个属性测试至少运行 100 次迭代。

**运行属性测试:**
```bash
pytest tests/property/ -v
```

### 集成测试 (Integration Tests)

集成测试验证多个组件协同工作，可能需要外部服务（如 MySQL、Ollama、WeWe-RSS）。

**运行集成测试:**
```bash
pytest tests/integration/ -v -m integration
```

**注意:** 集成测试需要以下服务运行：
- MySQL 数据库
- WeWe-RSS 服务
- Ollama 服务（可选）

## 安装测试依赖

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 或者只安装测试依赖
pip install pytest pytest-cov pytest-mock hypothesis
```

## 运行测试

### 运行所有测试

```bash
pytest
```

### 运行特定类型的测试

```bash
# 只运行单元测试
pytest tests/unit/

# 只运行属性测试
pytest tests/property/

# 只运行集成测试（需要外部服务）
pytest tests/integration/ -m integration
```

### 运行特定测试文件

```bash
pytest tests/unit/test_config.py -v
```

### 运行特定测试函数

```bash
pytest tests/unit/test_config.py::test_settings_with_all_required_fields -v
```

### 生成测试覆盖率报告

```bash
# 生成 HTML 覆盖率报告
pytest --cov=. --cov-report=html --cov-report=term

# 查看报告
# 打开 htmlcov/index.html
```

### 运行测试并显示详细输出

```bash
pytest -v -s
```

## 测试标记 (Markers)

测试使用 pytest markers 进行分类：

- `@pytest.mark.unit`: 单元测试
- `@pytest.mark.property`: 属性测试
- `@pytest.mark.integration`: 集成测试（需要外部服务）
- `@pytest.mark.slow`: 慢速测试

**按标记运行测试:**
```bash
# 只运行集成测试
pytest -m integration

# 排除慢速测试
pytest -m "not slow"

# 运行单元测试和属性测试
pytest -m "unit or property"
```

## 环境配置

测试使用独立的配置，不会影响生产环境。

### 单元测试和属性测试

使用内存数据库（SQLite）和 mock 对象，不需要外部服务。

### 集成测试

需要配置以下环境变量（或使用 `.env.test` 文件）：

```bash
# WeWe-RSS
WEWE_RSS_URL=http://localhost:4000
AUTH_CODE=test_auth_code

# 数据库
DB_HOST=127.0.0.1
DB_PORT=3308
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=test_analysis_ollama

# Ollama
OLLAMA_BASE_URL=http://192.168.10.43:11434
MODEL_NAME=deepseek-r1:32b

# 企业微信
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/your_webhook_url
```

## 持续集成 (CI/CD)

在 CI/CD 环境中，建议：

1. 始终运行单元测试和属性测试
2. 在有外部服务的环境中运行集成测试
3. 生成测试覆盖率报告

**示例 CI 配置:**
```yaml
# .github/workflows/test.yml
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v2
    - name: Install dependencies
      run: pip install -r requirements.txt -r requirements-dev.txt
    - name: Run unit tests
      run: pytest tests/unit/ tests/property/ -v --cov
    - name: Run integration tests
      run: pytest tests/integration/ -m integration -v
      if: ${{ env.HAS_EXTERNAL_SERVICES == 'true' }}
```

## 编写新测试

### 单元测试示例

```python
def test_my_function():
    """测试 my_function 的基本功能"""
    result = my_function(input_data)
    assert result == expected_output
```

### 属性测试示例

```python
from hypothesis import given, strategies as st, settings

@given(
    input_value=st.text(min_size=1, max_size=100)
)
@settings(max_examples=100)
def test_property_my_function(input_value):
    """
    Feature: my-feature, Property X: 描述属性
    
    对于任何有效输入，函数应该满足某个属性
    """
    result = my_function(input_value)
    assert some_property_holds(result)
```

### 集成测试示例

```python
import pytest

@pytest.mark.integration
def test_integration_my_service():
    """测试服务集成"""
    # 需要外部服务运行
    service = MyService()
    result = service.call_external_api()
    assert result is not None
```

## 故障排查

### 测试失败

1. 检查错误消息和堆栈跟踪
2. 使用 `-v -s` 选项查看详细输出
3. 检查环境变量配置
4. 确保外部服务正在运行（集成测试）

### 导入错误

确保项目根目录在 Python 路径中：
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### 数据库错误

集成测试需要 MySQL 数据库运行。确保：
- MySQL 服务正在运行
- 数据库凭据正确
- 测试数据库已创建

## 测试覆盖率目标

- 单元测试覆盖率: ≥ 80%
- 关键路径覆盖率: 100%（RSS 采集、LLM 分析、数据库操作）
- 属性测试: 覆盖所有设计文档中定义的属性

## 参考资料

- [Pytest 文档](https://docs.pytest.org/)
- [Hypothesis 文档](https://hypothesis.readthedocs.io/)
- [pytest-cov 文档](https://pytest-cov.readthedocs.io/)
