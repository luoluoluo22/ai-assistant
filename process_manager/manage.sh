#!/bin/bash

# 颜色设置
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 PM2 是否安装
check_pm2() {
    if ! command -v pm2 &> /dev/null; then
        echo -e "${YELLOW}PM2 未安装，正在安装...${NC}"
        if ! command -v npm &> /dev/null; then
            echo -e "${RED}请先安装 Node.js 和 npm，然后重试${NC}"
            exit 1
        fi
        npm install -g pm2
    fi
}

# 创建日志目录
mkdir -p ../logs

# 定义帮助信息
show_help() {
    echo -e "${GREEN}AI Assistant 服务管理脚本${NC}"
    echo "用法: $0 [命令]"
    echo
    echo "可用命令:"
    echo "  start     - 启动所有服务"
    echo "  stop      - 停止所有服务"
    echo "  restart   - 重启所有服务"
    echo "  status    - 查看服务状态"
    echo "  logs      - 查看所有日志"
    echo "  log-api   - 查看 FastAPI 服务日志"
    echo "  log-token - 查看 Token 服务日志"
    echo "  monitor   - 打开 PM2 监控界面"
    echo "  help      - 显示此帮助信息"
}

# 检查 PM2
check_pm2

# 根据参数执行相应操作
case "$1" in
    start)
        echo -e "${GREEN}启动所有服务...${NC}"
        pm2 start ecosystem.config.js
        ;;
    stop)
        echo -e "${YELLOW}停止所有服务...${NC}"
        pm2 stop all
        ;;
    restart)
        echo -e "${YELLOW}重启所有服务...${NC}"
        pm2 restart all
        ;;
    status)
        echo -e "${GREEN}服务状态:${NC}"
        pm2 status
        ;;
    logs)
        echo -e "${GREEN}显示所有日志:${NC}"
        pm2 logs
        ;;
    log-api)
        echo -e "${GREEN}显示 FastAPI 服务日志:${NC}"
        pm2 logs fastapi
        ;;
    log-token)
        echo -e "${GREEN}显示 Token 服务日志:${NC}"
        pm2 logs token_service
        ;;
    monitor)
        echo -e "${GREEN}打开监控界面...${NC}"
        pm2 monit
        ;;
    help|*)
        show_help
        ;;
esac 