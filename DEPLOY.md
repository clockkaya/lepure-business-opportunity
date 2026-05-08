# Lepure Business Opportunity - 部署指南

本文档介绍如何使用 `deploy/` 目录下的自动化脚本，无损并且快速地导出并在服务器部署更新 `lepure-business-opportunity` 环境。

---

## 部署流程架构图

整个自动化部署分为**导出与上传（本地）** 和 **清理与重部署（服务器）** 两个阶段：

1. **本地机器**: 通过 `export-and-upload.sh` 判断存在必备配置与镜像，自动压成 Tar 包并 SCP 到远程服务器。
2. **服务器**: 通过 `cleanup-and-redeploy.sh` 平滑停止当前业务容器，导入解压最新镜像和配置，无损重启服务，并可选择是否初始化数据库结构。

有关初始化机制：脚本会提示是否需要执行 `analysis-ollama/scripts/init_db.sql`，执行操作纯 SQL 注入不依赖服务器 Python 环境。

---

## 一、本地打包和上传 (export)

在项目根目录下（即包含 `docker-compose.yml` 的位置）执行导出脚本，同时指定版本标签。例如参数为 `v100`。
> 注意：确保你本地或者 WSL/Git Bash 下支持 `bash` 环境以及 `docker CLI` 命令。

```bash
bash deploy/export-and-upload.sh v100
```

### 导出前检查项:
1. 确保你有该项目依赖的镜像包：由于配置了指定版本，你需要保证 `lepure/wewe-rss:2.6.1` 以及自行 build 完毕的 `lepure/analysis-ollama:1.0.0` 在你本地系统中 `docker images` 存在。
2. 确保环境配置文件在根目录及子目录确实存在：包含 `.env` / `.env.example`，`wewe-rss/.env`，`analysis-ollama/.env.pre` 等文件。
3. 按照提示选择是否自动上传（默认上传目录为服务器 `~/` 家庭目录）。配置的服务器在脚本里面默认为 `8.130.102.166` ，你能够直接 `vim deploy/export-and-upload.sh` 进行二次更改。

*导出并在询问 "是否立即上传到服务器...?" 时输入 `y` 即可。*

---

## 二、服务器清理和重部署 (redeploy)

登入你的服务器。脚本（如果此前上传成功）及配置包 / 镜像包均会在你服务器登录用户的 home 目录 （`~/`）。

```bash
ssh huxiaohang@8.130.102.166

# 赋予执行权限并执行部署
chmod +x ~/cleanup-and-redeploy.sh
bash ~/cleanup-and-redeploy.sh v100
```

### 部署过程行为:
1. **清理旧部署容器**: 寻找 `/opt/lepure-business-opportunity` 进行 `docker compose down`。脚本明确不带 `-v` 参数，**绝对不会**抹除您的 MySQL 业务数据和 RSS 任何有价记录存储。
2. **配置文件平移**: 新代码和环境变量会在解压后平替到 `/opt/lepure-business-opportunity` 内，对旧配置文件如有需要建议提早备份。
3. **数据库初始化检测**: 容器拉起后（约等待 15 秒），脚本会弹出提示：
   `【数据库操作】这是全新的部署环境吗？是否需要执行 init_db.sql 初始化表结构？(y/n)`
   - 对于日常滚动更新（数据早就存在）：请输入 `n`。
   - 如果是一台白板新机器初次部署：输入 `y`。它会自动将附带打包的 `init_db.sql` 应用进数据库而不必手工排查。

### 检查最终运行状态
```bash
cd /opt/lepure-business-opportunity
docker compose ps
docker compose logs -f agent
```
