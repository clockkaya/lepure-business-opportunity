#!/bin/bash

main() {
    # 检查是否提供了版本参数
    if [ -z "$1" ]; then
        echo "错误：请提供版本号"
        echo "用法: ./cleanup-and-redeploy.sh <版本号>"
        echo "示例: ./cleanup-and-redeploy.sh v100"
        echo ""
        return 1
    fi

    VERSION="$1"
    DEPLOY_DIR="/opt/lepure-business-opportunity"

    echo "=== 开始清理旧部署并部署新版本: $VERSION ==="

    # 1. 停止并删除运行中的容器（如果存在）
    if [ -d "$DEPLOY_DIR" ]; then
        echo "由于本次要求无损更新，将只停止容器，不删除 MySQL 数据卷。"
        # 执行平滑停止
        cd "$DEPLOY_DIR" && sudo docker compose down || true
    else
        echo "未发现旧部署目录，跳过容器停止步骤"
    fi

    # 2. 检查必需的文件是否存在（在用户家目录，默认当前执行路径为家目录 ~/）
    if [ ! -f ~/lepure-opportunity-images-${VERSION}.tar ] || [ ! -f ~/lepure-opportunity-configs-${VERSION}.tar.gz ]; then
        echo "错误：未在当前目录找到必需的文件"
        echo "请确保以下文件存在："
        echo "  ~/lepure-opportunity-images-${VERSION}.tar"
        echo "  ~/lepure-opportunity-configs-${VERSION}.tar.gz"
        echo ""
        return 1
    fi

    # 3. 删除旧版本的解压镜像和压缩包 (非挂载卷和项目目录自身)
    echo "清理旧的 Docker 资源和历史部署压缩包..."
    sudo rm -f /opt/lepure-opportunity-images-*.tar || true
    sudo rm -f /opt/lepure-opportunity-configs-*.tar.gz || true
    sudo docker system prune -f || true

    # 4. 移动文件到 /opt
    echo "移动文件到 /opt..."
    sudo mv ~/lepure-opportunity-images-${VERSION}.tar ~/lepure-opportunity-configs-${VERSION}.tar.gz /opt/

    # 5. 加载镜像（可能比较缓慢）
    echo "加载 Docker 镜像（可能需要 2-5 分钟）..."
    sudo docker load -i /opt/lepure-opportunity-images-${VERSION}.tar

    # 6. 解压当前版本配置文件并覆盖部署目录
    echo "解压配置文件..."
    sudo mkdir -p "$DEPLOY_DIR"
    sudo tar -xzf /opt/lepure-opportunity-configs-${VERSION}.tar.gz -C "$DEPLOY_DIR"

    # 7. 配置环境变量
    echo "配置环境变量..."
    cd "$DEPLOY_DIR"
    
    # 针对根目录环境
    if [ ! -f .env ] && [ -f .env.example ]; then
        echo "未找到根目录 .env 文件，正从 .env.example 生成..."
        sudo cp .env.example .env
        sudo chmod 600 .env
        echo "警告：请务必检查根目录 .env 文件，填入 MySQL 真实密码配置"
    fi
    
    # 针对 analysis-ollama
    if [ ! -f ./analysis-ollama/.env ] && [ -f ./analysis-ollama/.env.pre ]; then
        echo "正在复制 analysis-ollama 的环境变量..."
        sudo cp ./analysis-ollama/.env.pre ./analysis-ollama/.env
    fi

    # 8. 启动服务
    echo "启动 Docker 服务..."
    sudo docker compose up -d

    # 9. 数据库初始化检测
    echo "======================================"
    read -p "【数据库操作】这是全新的部署环境吗？是否需要执行 init_db.sql 初始化表结构？（选 y 将执行初始化结构，不影响已有数据）(y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "等待 MySQL 服务可用 (15秒)..."
        sleep 15
        
        # 提取根目录 .env 的 MySQL Root 密码
        DB_PASSWORD=$(sudo grep "^MYSQL_ROOT_PASSWORD=" .env | cut -d '=' -f2- | tr -d '"' | tr -d "'" | tr -d '\r' | xargs)
        
        if [ -z "$DB_PASSWORD" ]; then
            echo "错误：未能从 .env 文件中提取到 MYSQL_ROOT_PASSWORD，无法应用初始化。"
        else
            if sudo test -f "./analysis-ollama/scripts/init_db.sql"; then
                echo "开始应用数据库初始化..."
                sudo docker exec -i -e MYSQL_PWD="${DB_PASSWORD}" opportunity-db mysql -uroot < "./analysis-ollama/scripts/init_db.sql"
                
                if [ $? -eq 0 ]; then
                    echo "数据库初始化脚本应用成功！"
                else
                    echo "警告：数据库初始化过程中出现错误，请视情况登录容器排查！"
                fi
            else
                echo "错误：未发现对应的 SQL 文件 (analysis-ollama/scripts/init_db.sql)"
            fi
        fi
    else
        echo "跳过数据库初始化步骤。"
    fi

    # 10. 查看状态（需要 sudo）
    echo ""
    echo "=== 版本 $VERSION 部署完成 ==="
    echo "查看服务状态："
    sudo docker compose ps
    echo ""
    echo "查看日志命令（例如 Agent）："
    echo "  sudo docker compose logs -f agent"
}

# 调用主函数
main "$@"
