# 配置管理指南

本文档说明如何管理 lepure-business-opportunity 项目的配置，确保 wewe-rss 和 analysis-ollama 两个服务使用一致的配置。

## 配置文件结构

```
lepure-business-opportunity/
├── wewe-rss/
│   ├── .env                    # WeWe-RSS 实际配置（不提交到 Git）
│   ├── .env.example            # WeWe-RSS 配置模板
│   └── docker-compose.yml      # 引用 .env 文件
│
└── analysis-ollama/
    ├── .env.dev                # 开发环境实际配置（不提交到 Git）
    ├── .env.dev.example        # 开发环境配置模板
    ├── .env.pre                # 预发布环境实际配置（不提交到 Git）
    ├── .env.pre.example        # 预发布环境配置模板
    └── docker-compose.dev.yml  # 引用 .env.dev 文件
```

## 共享配置项

以下配置项在两个服务之间共享，**必须保持一致**：

### 1. MySQL Root 密码

- **wewe-rss/.env**: `MYSQL_ROOT_PASSWORD`
- **analysis-ollama/.env.dev**: `DB_PASSWORD`
- **analysis-ollama/.env.pre**: `DB_PASSWORD`

**重要**: 这三个配置项必须使用相同的值！

### 2. WeWe-RSS 认证码

- **wewe-rss/.env**: `AUTH_CODE`
- **analysis-ollama/.env.dev**: `AUTH_CODE`
- **analysis-ollama/.env.pre**: `AUTH_CODE`

**重要**: 这三个配置项必须使用相同的值！

## 初始化配置步骤

### 第一步：配置 WeWe-RSS

1. 复制配置模板：
   ```bash
   cd wewe-rss
   cp .env.example .env
   ```

2. 编辑 `wewe-rss/.env`，设置你的密码和认证码：
   ```env
   MYSQL_ROOT_PASSWORD=your_strong_password_here
   AUTH_CODE=your_auth_code_here
   ```

### 第二步：配置 Analysis-Ollama（开发环境）

1. 复制配置模板：
   ```bash
   cd analysis-ollama
   cp .env.dev.example .env.dev
   ```

2. 编辑 `analysis-ollama/.env.dev`，**使用与 wewe-rss 相同的密码和认证码**：
   ```env
   DB_PASSWORD=your_strong_password_here  # 必须与 wewe-rss/.env 中的 MYSQL_ROOT_PASSWORD 相同
   AUTH_CODE=your_auth_code_here          # 必须与 wewe-rss/.env 中的 AUTH_CODE 相同
   ```

3. 配置其他必需项：
   ```env
   OLLAMA_BASE_URL=http://192.168.10.43:11434
   MODEL_NAME=deepseek-r1:32b
   WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key
   ```

### 第三步：配置 Analysis-Ollama（预发布环境）

1. 复制配置模板：
   ```bash
   cd analysis-ollama
   cp .env.pre.example .env.pre
   ```

2. 编辑 `analysis-ollama/.env.pre`，**使用与 wewe-rss 相同的密码和认证码**：
   ```env
   DB_PASSWORD=your_strong_password_here  # 必须与 wewe-rss/.env 中的 MYSQL_ROOT_PASSWORD 相同
   AUTH_CODE=your_auth_code_here          # 必须与 wewe-rss/.env 中的 AUTH_CODE 相同
   ```

## 配置验证清单

在启动服务之前，请验证以下配置项：

- [ ] `wewe-rss/.env` 文件已创建
- [ ] `analysis-ollama/.env.dev` 文件已创建（开发环境）
- [ ] `analysis-ollama/.env.pre` 文件已创建（预发布环境）
- [ ] MySQL 密码在所有配置文件中一致
- [ ] AUTH_CODE 在所有配置文件中一致
- [ ] Ollama 服务地址正确
- [ ] 企业微信 Webhook URL 已配置

## 常见问题

### Q1: 为什么应用无法连接到数据库？

**A**: 检查 `wewe-rss/.env` 中的 `MYSQL_ROOT_PASSWORD` 是否与 `analysis-ollama/.env.dev` 中的 `DB_PASSWORD` 一致。

### Q2: 如何修改 MySQL 密码？

**A**: 需要同时修改三个地方：
1. `wewe-rss/.env` 中的 `MYSQL_ROOT_PASSWORD`
2. `wewe-rss/.env` 中的 `DATABASE_URL`（URL 中的密码部分）
3. `analysis-ollama/.env.dev` 和 `.env.pre` 中的 `DB_PASSWORD`

然后重新启动所有服务：
```bash
cd wewe-rss
docker-compose down -v  # 清理旧数据
docker-compose up -d

cd ../analysis-ollama
docker-compose -f docker-compose.dev.yml restart
```

### Q3: 如何修改 AUTH_CODE？

**A**: 需要同时修改三个地方：
1. `wewe-rss/.env` 中的 `AUTH_CODE`
2. `analysis-ollama/.env.dev` 中的 `AUTH_CODE`
3. `analysis-ollama/.env.pre` 中的 `AUTH_CODE`

然后重启服务：
```bash
cd wewe-rss
docker-compose restart

cd ../analysis-ollama
docker-compose -f docker-compose.dev.yml restart
```

### Q4: .env 文件为什么不提交到 Git？

**A**: .env 文件包含敏感信息（密码、Webhook URL），不应该提交到版本控制系统。项目提供了 .env.example 模板文件供参考。

## 安全建议

1. **使用强密码**: `MYSQL_ROOT_PASSWORD` 应该是一个强密码（至少 16 个字符，包含大小写字母、数字和特殊字符）
2. **保护 Webhook URL**: `WECOM_WEBHOOK_URL` 包含密钥，不要泄露给未授权人员
3. **定期更换密码**: 建议定期更换数据库密码和认证码
4. **不要提交 .env 文件**: 确保 .gitignore 中包含 `.env`、`.env.dev`、`.env.pre`

## 配置文件示例

### wewe-rss/.env（示例）
```env
MYSQL_ROOT_PASSWORD=MyStr0ng!Pass@2024
MYSQL_DATABASE=wewe-rss
AUTH_CODE=abc123xyz789
TZ=Asia/Shanghai
PLATFORM_URL=https://weread.965111.xyz
DATABASE_URL=mysql://root:MyStr0ng!Pass@2024@db:3306/wewe-rss?schema=public&connect_timeout=30&pool_timeout=30&socket_timeout=30
```

### analysis-ollama/.env.dev（示例）
```env
ENV=dev
POLL_INTERVAL_MINUTES=60
WEWE_RSS_URL=http://localhost:4000
AUTH_CODE=abc123xyz789
DB_HOST=127.0.0.1
DB_PORT=3308
DB_USER=root
DB_PASSWORD=MyStr0ng!Pass@2024
DB_NAME=analysis_ollama
OLLAMA_BASE_URL=http://192.168.10.43:11434
MODEL_NAME=deepseek-r1:32b
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx
LOG_LEVEL=INFO
```

## 总结

通过将配置提取到 .env 文件中，我们实现了：

1. ✅ **单一数据源**: MySQL 密码和 AUTH_CODE 只需在一个地方定义
2. ✅ **易于维护**: 修改配置时只需更新对应的 .env 文件
3. ✅ **安全性**: 敏感信息不会提交到 Git
4. ✅ **清晰的文档**: .env.example 文件提供了配置模板和说明
