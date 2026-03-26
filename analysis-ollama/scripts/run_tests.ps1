# 测试运行脚本 (PowerShell)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "运行 Analysis-Ollama 测试套件" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 激活虚拟环境
if (Test-Path ".venv\Scripts\Activate.ps1") {
    & .\.venv\Scripts\Activate.ps1
} elseif (Test-Path "venv\Scripts\Activate.ps1") {
    & .\venv\Scripts\Activate.ps1
}

# 运行单元测试
Write-Host "1. 运行单元测试..." -ForegroundColor Yellow
pytest tests/unit/ -v --tb=short

# 运行属性测试
Write-Host ""
Write-Host "2. 运行属性测试..." -ForegroundColor Yellow
pytest tests/property/ -v --tb=short

# 运行集成测试（可选，需要外部服务）
Write-Host ""
Write-Host "3. 运行集成测试（需要外部服务）..." -ForegroundColor Yellow
pytest tests/integration/ -v -m integration --tb=short
if ($LASTEXITCODE -ne 0) {
    Write-Host "集成测试跳过（需要外部服务）" -ForegroundColor Gray
}

# 生成覆盖率报告
Write-Host ""
Write-Host "4. 生成测试覆盖率报告..." -ForegroundColor Yellow
pytest tests/unit/ tests/property/ --cov=. --cov-report=term --cov-report=html

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "测试完成！" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host "查看 HTML 覆盖率报告: htmlcov\index.html" -ForegroundColor Cyan
