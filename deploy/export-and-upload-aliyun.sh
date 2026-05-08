#!/bin/bash

main() {
    # 检查是否提供了版本参数
    if [ -z "$1" ]; then
        echo "错误：请提供版本号"
        echo "用法: ./export-and-upload.sh <版本号>"
        echo "示例: ./export-and-upload.sh v100"
        echo ""
        return 1
    fi

    # 配置变量
    VERSION="$1"
    REMOTE_USER="huxiaohang"
    REMOTE_HOST="8.130.102.166"  # 根据需要进行修改
    
    WEWE_IMAGE="lepure/wewe-rss:2.6.1"
    AGENT_IMAGE="lepure/analysis-ollama:1.0.0"

    echo "=== 开始导出部署文件 (版本: $VERSION) ==="

    # 1. 清理旧版本的 tar 包
    echo "清理旧版本的部署文件..."
    OLD_IMAGES=$(ls lepure-opportunity-images-*.tar 2>/dev/null || true)
    OLD_CONFIGS=$(ls lepure-opportunity-configs-*.tar.gz 2>/dev/null || true)
    
    if [ -n "$OLD_IMAGES" ] || [ -n "$OLD_CONFIGS" ]; then
        echo "找到以下旧文件："
        [ -n "$OLD_IMAGES" ] && echo "$OLD_IMAGES"
        [ -n "$OLD_CONFIGS" ] && echo "$OLD_CONFIGS"
        
        read -p "是否删除这些旧文件? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -f lepure-opportunity-images-*.tar lepure-opportunity-configs-*.tar.gz 2>/dev/null || true
            echo "已删除旧文件"
        else
            echo "保留旧文件"
        fi
    else
        echo "未发现旧版本文件"
    fi
    echo ""

    # 2. 检查必需文件是否存在
    echo "检查必需文件..."
    REQUIRED_FILES=("docker-compose.yml" "wewe-rss/.env" "analysis-ollama/.env.pre" "analysis-ollama/scripts/init_db.sql")
    # 支持根目录使用 .env.example 或 .env
    if [ -e ".env" ]; then
        REQUIRED_FILES+=(".env")
    elif [ -e ".env.example" ]; then
        REQUIRED_FILES+=(".env.example")
    else
        echo "错误：未找到根目录的 .env 或 .env.example"
        echo ""
        return 1
    fi

    for file in "${REQUIRED_FILES[@]}"; do
        if [ ! -e "$file" ]; then
            echo "错误：未找到必需的文件或目录: $file"
            echo "请确保你在项目根目录执行此脚本"
            echo ""
            return 1
        fi
    done

    # 3. 检查 Docker 镜像是否存在
    echo "检查 Docker 镜像..."
    if ! docker images | grep -q "$(echo $WEWE_IMAGE | cut -d':' -f1)"; then
        echo "错误：未找到镜像 $WEWE_IMAGE"
        echo "请确保该镜像存在于本地 (可以执行 docker pull lepure/wewe-rss:2.6.1 或者本地构建)"
        echo ""
        return 1
    fi

    if ! docker images | grep -q "$(echo $AGENT_IMAGE | cut -d':' -f1)"; then
        echo "错误：未找到镜像 $AGENT_IMAGE"
        echo "请先构建 agent 镜像 (docker build -t $AGENT_IMAGE ./analysis-ollama)"
        echo ""
        return 1
    fi

    # 4. 导出 Docker 镜像
    echo "导出 Docker 镜像（可能需要几分钟）..."
    docker save -o lepure-opportunity-images-${VERSION}.tar $WEWE_IMAGE $AGENT_IMAGE

    if [ $? -ne 0 ]; then
        echo "错误：Docker 镜像导出失败"
        echo ""
        return 1
    fi

    echo "镜像导出完成: lepure-opportunity-images-${VERSION}.tar"

    # 5. 打包配置文件
    echo "打包配置文件..."
    # 动态确定需要打包的根目录 env 文件
    ROOT_ENV_FILE=".env.example"
    if [ -e ".env" ]; then
        ROOT_ENV_FILE=".env"
    fi

    tar -czf lepure-opportunity-configs-${VERSION}.tar.gz docker-compose.yml "$ROOT_ENV_FILE" wewe-rss/.env analysis-ollama/.env.pre analysis-ollama/scripts/init_db.sql

    if [ $? -ne 0 ]; then
        echo "错误：配置文件打包失败"
        echo ""
        return 1
    fi

    echo "配置打包完成: lepure-opportunity-configs-${VERSION}.tar.gz"

    # 6. 显示文件信息
    echo ""
    echo "=== 导出完成 ==="
    echo "生成的文件："
    ls -lh lepure-opportunity-images-${VERSION}.tar lepure-opportunity-configs-${VERSION}.tar.gz

    # 7. 上传到服务器
    echo ""
    read -p "是否立即上传到服务器 ${REMOTE_USER}@${REMOTE_HOST}? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "开始上传文件到服务器..."
        scp lepure-opportunity-images-${VERSION}.tar lepure-opportunity-configs-${VERSION}.tar.gz deploy/cleanup-and-redeploy.sh ${REMOTE_USER}@${REMOTE_HOST}:~/
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "=== 上传完成 ==="
            echo "文件已上传到服务器 ~/ 目录"
            echo ""
            echo "下一步：SSH 登录服务器并执行部署脚本"
            echo "  ssh ${REMOTE_USER}@${REMOTE_HOST}"
            echo "  chmod +x ~/cleanup-and-redeploy.sh"
            echo "  ./cleanup-and-redeploy.sh ${VERSION}"
        else
            echo "错误：文件上传失败"
            echo ""
            return 1
        fi
    else
        echo ""
        echo "跳过上传。手动上传命令："
        echo "  scp lepure-opportunity-images-${VERSION}.tar lepure-opportunity-configs-${VERSION}.tar.gz deploy/cleanup-and-redeploy.sh ${REMOTE_USER}@${REMOTE_HOST}:~/"
    fi
}

# 调用主函数
main "$@"
