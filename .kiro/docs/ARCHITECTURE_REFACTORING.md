# 架构重构：移除 core/ 目录

## 问题分析

### 原始结构的问题

```
core/
├── processor.py      # 业务编排
└── health_check.py   # 启动检查

services/
├── rss_service.py
├── llm_service.py
└── notification_service.py
```

**问题**:
1. **`core/` 和 `services/` 职责重叠**
   - `processor.py` 本质上就是一个 service
   - 它编排其他 services，但自己也是 service
   
2. **`core/` 命名模糊**
   - 不清楚 "core" 的具体含义
   - 容易与 "核心业务逻辑" 混淆
   
3. **`health_check.py` 放错位置**
   - 它是工具函数，不是业务逻辑
   - 应该放在 `utils/` 或直接在 `main.py`

4. **不符合 Python 最佳实践**
   - Python/FastAPI 项目通常没有 `core/` 目录
   - 所有业务逻辑都在 `services/` 或 `api/`

---

## Python/FastAPI 最佳实践

### 推荐的项目结构

```
project/
├── models/          # 数据模型（SQLModel/Pydantic）
├── services/        # 所有业务逻辑服务
├── api/             # API 路由（如果是 Web 应用）
├── utils/           # 工具函数
├── config/          # 配置
└── main.py          # 应用入口
```

**关键原则**:
- **services/** 包含所有业务逻辑
- **utils/** 包含工具函数和辅助功能
- **不需要 core/** 目录

---

## 重构方案

### 1. 移动 `processor.py` → `services/article_processor.py`

**理由**: 
- `ArticleProcessor` 是一个业务服务
- 它编排其他 services，但本质上也是 service
- 应该和其他 services 放在一起

**重命名理由**:
- `processor.py` → `article_processor.py` 更明确
- 避免与通用的 "processor" 概念混淆
- 清楚表明它处理的是文章相关业务

### 2. 移动 `health_check.py` → `utils/health_check.py`

**理由**:
- `health_check` 是工具函数，不是业务逻辑
- 它提供启动时的检查功能
- 应该放在 `utils/` 目录

### 3. 删除 `core/` 目录

**理由**:
- 目录已空，不再需要
- 简化项目结构
- 符合 Python 最佳实践

---

## 重构后的结构

```
analysis-ollama/
├── models/                      # 数据模型
│   ├── article.py              # Article 模型 + 查询方法
│   ├── project.py              # ExtractedProject 模型 + 查询方法
│   └── feed_config.py          # FeedConfig（未来扩展）
├── services/                    # 业务逻辑层（统一）
│   ├── article_processor.py    # 文章处理服务（原 core/processor.py）
│   ├── rss_service.py          # RSS 采集服务
│   ├── llm_service.py          # LLM 分析服务
│   └── notification_service.py # 通知服务
├── utils/                       # 工具层
│   ├── db_utils.py             # 数据库工具
│   ├── logger.py               # 日志工具
│   ├── html_parser.py          # HTML 解析
│   └── health_check.py         # 健康检查（原 core/health_check.py）
├── config/                      # 配置层
│   └── settings.py
├── main.py                      # 应用入口
└── docs/                        # 文档
```

**优势**:
- ✅ 结构清晰，职责明确
- ✅ 所有业务逻辑在 `services/`
- ✅ 所有工具函数在 `utils/`
- ✅ 符合 Python/FastAPI 最佳实践
- ✅ 更容易理解和维护

---

## 对比：重构前后

### 重构前（混乱）

```python
# main.py
from core.health_check import run_health_checks
from core.processor import ArticleProcessor
from services.rss_service import RSSService
```

**问题**: `core` 和 `services` 混在一起，不清楚区别

### 重构后（清晰）

```python
# main.py
from utils.health_check import run_health_checks
from services.article_processor import ArticleProcessor
from services.rss_service import RSSService
```

**优势**: 
- 工具函数在 `utils`
- 业务逻辑在 `services`
- 职责清晰

---

## 业界参考

### FastAPI 官方项目结构

```
fastapi-project/
├── app/
│   ├── models/
│   ├── services/      # 或 crud/
│   ├── api/
│   ├── core/          # 注意：FastAPI 的 core 是配置和安全
│   │   ├── config.py
│   │   └── security.py
│   └── main.py
```

**注意**: FastAPI 的 `core/` 通常只包含：
- 配置（config.py）
- 安全相关（security.py）
- 依赖注入（dependencies.py）

**不包含**: 业务逻辑或工具函数

### Django 项目结构

```
django-project/
├── apps/
│   └── myapp/
│       ├── models.py
│       ├── views.py
│       ├── services.py    # 业务逻辑
│       └── utils.py       # 工具函数
```

**注意**: Django 也没有 `core/` 目录用于业务逻辑

---

## 命名最佳实践

### services/ 目录命名规范

**推荐**:
- `article_processor.py` - 明确表明处理文章
- `rss_service.py` - RSS 相关服务
- `llm_service.py` - LLM 相关服务
- `notification_service.py` - 通知相关服务

**避免**:
- `processor.py` - 太通用，不清楚处理什么
- `core.py` - 太模糊
- `handler.py` - 不清楚处理什么

### utils/ 目录命名规范

**推荐**:
- `health_check.py` - 健康检查工具
- `db_utils.py` - 数据库工具
- `logger.py` - 日志工具
- `html_parser.py` - HTML 解析工具

**特点**: 都是工具函数，不包含业务逻辑

---

## 迁移清单

### 文件移动

- [x] `core/processor.py` → `services/article_processor.py`
- [x] `core/health_check.py` → `utils/health_check.py`
- [x] 删除 `core/__init__.py`
- [x] 删除 `core/` 目录

### 导入更新

- [x] `main.py` - 更新导入路径
- [x] 其他文件 - 检查是否有引用 `core/`

### 测试验证

- [ ] 运行 `python main.py` 验证启动
- [ ] 检查所有导入正常
- [ ] 验证功能正常

---

## 总结

### 重构原因
1. **消除混淆**: `core/` 和 `services/` 职责重叠
2. **符合最佳实践**: Python/FastAPI 项目通常没有 `core/` 用于业务逻辑
3. **提高可维护性**: 结构更清晰，职责更明确

### 重构结果
- ✅ 所有业务逻辑在 `services/`
- ✅ 所有工具函数在 `utils/`
- ✅ 删除了混淆的 `core/` 目录
- ✅ 符合 Python 最佳实践

### 关键原则
- **services/** = 业务逻辑
- **utils/** = 工具函数
- **models/** = 数据模型
- **config/** = 配置
- **main.py** = 应用入口

**这才是 Python 项目的正确结构！** 🎯
