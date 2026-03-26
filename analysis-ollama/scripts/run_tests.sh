#!/bin/bash
# 测试运行脚本

echo "=========================================="
echo "运行 Analysis-Ollama 测试套件"
echo "=========================================="
echo ""

# 激活虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# 运行单元测试
echo "1. 运行单元测试..."
pytest tests/unit/ -v --tb=short

# 运行属性测试
echo ""
echo "2. 运行属性测试..."
pytest tests/property/ -v --tb=short

# 运行集成测试（可选，需要外部服务）
echo ""
echo "3. 运行集成测试（需要外部服务）..."
pytest tests/integration/ -v -m integration --tb=short || echo "集成测试跳过（需要外部服务）"

# 生成覆盖率报告
echo ""
echo "4. 生成测试覆盖率报告..."
pytest tests/unit/ tests/property/ --cov=. --cov-report=term --cov-report=html

echo ""
echo "=========================================="
echo "测试完成！"
echo "=========================================="
echo "查看 HTML 覆盖率报告: htmlcov/index.html"
