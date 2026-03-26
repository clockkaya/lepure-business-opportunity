# WeWe-RSS 与 AI 总结流程总结文档

本文档总结了在此工作区（Workspace）中完成的 WeWe-RSS 本地部署、AI 总结定制化流程以及相关的关键技术点和坑点。方便您在切换工作区或未来维护时快速回顾。

## 1. 核心业务流程与架构

整个“微信文章自动抓取并总结”的流程架构分两部分：

1.  **数据抓取侧 (WeWe-RSS)**
    *   **部署方式**：基于 Windows WSL2 + Docker Desktop 运行。
    *   **职责**：定期通过微信中转服务（`weread.965111.xyz`）同步关注公众号的历史文章和增量文章，并暴露 RSS (Atom) 接口供外部系统消费。
    *   **存储逻辑**：为了防封号和减小数据库体积，WeWe-RSS 的 MySQL 数据库（端口 3308）默认**不存储纯文本或 HTML 正文**，只保留文章标题和链接等元数据。
2.  **数据处理侧 (Python 自动化脚本)**
    *   **脚本路径**：`F:\PROJECTS\lepure-ai-opportunity\process_rss.py` (此脚本千万**不要**删除！)
    *   **全文明文拉取**：脚本在请求 WeWe-RSS 的本地接口时，必须带上 `?mode=fulltext&update=true` 参数（例如 `http://localhost:4000/feeds/MP_WXS_XXX.atom?mode=fulltext&update=true`）。这样 WeWe-RSS 服务器就会在接到请求的瞬时，去微信页面把完整的 HTML 抓下来塞进 XML 返回。
    *   **文本提纯**：脚本使用 BeautifulSoup 精准定位微信文章的有效正文容器（`<div class="rich_media_content">`），剔除样式表和无效标签。
    *   **AI 总结**：清理后的纯文字长文会被发送给本地的 Ollama 模型（`deepseek-r1:32b`，位于 `192.168.10.43:11434`）进行提炼。

## 2. 踩过的坑与定制化修复

在验证和集成过程中，我们发现了 WeWe-RSS 的几个痛点，并直接在它的源码上进行了本地化改造（构建了自定义专属 Docker 镜像）。

### 问题 1：网络波动导致公众号卡死 (has_history=0)
**现象**：偶尔新建公众号时页面显示 0 篇文章，且后续怎样点更新都没用。
**原因**：由于 WeWe-RSS 内部有 15秒请求超时限制，如果首次尝试拉取历史文章时遇到源站响应慢或中转站压力大，WeWe-RSS 会以为抓完了，随即将数据库里的 `has_history` 状态锁定为 `0`（不再继续抓取历史）。
**解决方案**：
我们给 WeWe-RSS 的前后端增加了一个“后悔药”功能：
*   **后端** (`apps/server/src/trpc/trpc.router.ts`)：在更新接口里增加了接收 `hasHistory` 参数的能力。
*   **前端** (`apps/web/src/pages/feeds/index.tsx`)：在订阅页面操作区植入了一个**“重置状态”**（Reset Status）按钮。当遇到公众号卡死时，可以直接在界面上一键重置其同步状态，让系统恢复抓取。

### 问题 2：Docker 容器 8 小时时差
**现象**：Docker 后台日志及页面上显示的更新时间比北京时间晚了 8 个小时。
**原因**：基础镜像采用 UTC 时间。
**解决方案**：在 `docker-compose.yml` 的 `app` 服务中注入了 `TZ=Asia/Shanghai` 环境变量。

### 问题 3：Windows 本地编译 Docker 问题
**现象**：在使用 `docker compose up --build` 时，由于全局 `pnpm` 版本过高导致 Lockfile 验证失败，且 shell 脚本因 Windows 的 `\r` 换行符报错。
**解决方案**：修改 `Dockerfile`，强制降级安装兼容该仓库的 `pnpm@8.15.6`。 `\r` 导致的 Prisma 命令行 Help 显示属于正常报错范围，不影响业务本身的启动。

## 3. 文件清理确认

针对您的提问：`F:\PROJECTS\wewe-rss\*.py` 这些文件，**我已经全部帮您安全删除了**。

那几个文件（`inspect_db.py`, `fix_yimai.py` 等等）都是在排查“卡死假象”时，为了修改 MySQL 数据库状态而写的临时脚本。既然现在网页上已经有了“一键重置状态”的按钮，这些修数据库的脚本就彻底失去利用价值了。

*需要保留的脚本：刚才放在 `F:\PROJECTS\lepure-ai-opportunity\process_rss.py` 中的完整 Python AI 流程脚本需保留。*
