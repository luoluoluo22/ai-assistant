# PowerShell 管理脚本

# 颜色设置
$Red = "`e[31m"
$Green = "`e[32m"
$Yellow = "`e[33m"
$Reset = "`e[0m"

# 添加 npm 全局安装目录到 PATH
$env:PATH = "$env:APPDATA\npm;$env:PATH"

# 检查 PM2 是否安装
function Check-PM2 {
  try {
    pm2 --version | Out-Null
    return $true
  }
  catch {
    Write-Host "${Red}PM2 未安装. 正在安装...${Reset}"
    try {
      npm install -g pm2
      return $true
    }
    catch {
      Write-Host "${Red}请先安装 Node.js 和 npm，然后重试${Reset}"
      return $false
    }
  }
}

# 创建日志目录
function Create-LogDir {
  if (-not (Test-Path "../logs")) {
    New-Item -ItemType Directory -Path "../logs"
  }
}

# 显示帮助信息
function Show-Help {
  Write-Host "${Green}AI Assistant 服务管理脚本${Reset}"
  Write-Host "用法: .\manage.ps1 [命令]`n"
  Write-Host "可用命令:"
  Write-Host "  start     - 启动所有服务"
  Write-Host "  stop      - 停止所有服务"
  Write-Host "  restart   - 重启所有服务"
  Write-Host "  status    - 查看服务状态"
  Write-Host "  logs      - 查看所有日志"
  Write-Host "  log-api   - 查看 FastAPI 服务日志"
  Write-Host "  log-token - 查看 Token 服务日志"
  Write-Host "  monitor   - 打开监控界面"
  Write-Host "  help      - 显示此帮助信息"
}

# 主程序
if (-not (Check-PM2)) {
  exit 1
}

Create-LogDir

switch ($args[0]) {
  "start" {
    Write-Host "${Green}启动所有服务...${Reset}"
    pm2 start ecosystem.config.js
  }
  "stop" {
    Write-Host "${Yellow}停止所有服务...${Reset}"
    pm2 stop all
  }
  "restart" {
    Write-Host "${Yellow}重启所有服务...${Reset}"
    pm2 restart all
  }
  "status" {
    Write-Host "${Green}服务状态:${Reset}"
    pm2 status
  }
  "logs" {
    Write-Host "${Green}显示所有日志:${Reset}"
    pm2 logs
  }
  "log-api" {
    Write-Host "${Green}显示 FastAPI 服务日志:${Reset}"
    pm2 logs fastapi
  }
  "log-token" {
    Write-Host "${Green}显示 Token 服务日志:${Reset}"
    pm2 logs token_service
  }
  "monitor" {
    Write-Host "${Green}打开监控界面...${Reset}"
    pm2 monit
  }
  default {
    Show-Help
  }
} 