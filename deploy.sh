#!/bin/bash

# 输出颜色设置
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# 检查是否以 root 权限运行
if [ "$EUID" -ne 0 ]; then 
  echo -e "${RED}请使用 root 权限运行此脚本（sudo ./deploy.sh）${NC}"
  exit 1
fi

echo -e "${GREEN}开始部署 AI Assistant 服务...${NC}"

# 检查并安装 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${GREEN}正在安装 Docker...${NC}"
    apt-get update
    apt-get install -y ca-certificates curl gnupg
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

# 检查 Docker 是否安装成功
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker 安装失败，请手动安装后重试${NC}"
    exit 1
fi

echo -e "${GREEN}正在停止并删除旧容器（如果存在）...${NC}"
docker stop ai_assistant 2>/dev/null || true
docker rm ai_assistant 2>/dev/null || true

echo -e "${GREEN}正在构建 Docker 镜像...${NC}"
docker build -t ai_assistant .

echo -e "${GREEN}正在启动服务...${NC}"
docker run -d \
  --name ai_assistant \
  --restart unless-stopped \
  -p 8001:8001 \
  -v $(pwd)/data:/app/data \
  ai_assistant

# 检查容器是否成功运行
if [ "$(docker ps -q -f name=ai_assistant)" ]; then
    echo -e "${GREEN}服务部署成功！${NC}"
    echo -e "${GREEN}服务已在 http://localhost:8001 运行${NC}"
    echo -e "${GREEN}可以使用以下命令查看日志：${NC}"
    echo -e "docker logs -f ai_assistant"
else
    echo -e "${RED}服务启动失败，请检查日志：${NC}"
    docker logs ai_assistant
    exit 1
fi 