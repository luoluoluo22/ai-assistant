FROM ubuntu:22.04

WORKDIR /app

# 设置非交互式安装
ENV DEBIAN_FRONTEND=noninteractive

# 安装 Python、Node.js 和其他依赖
RUN apt-get update && apt-get install -y \
  python3.11 \
  python3.11-dev \
  python3-pip \
  build-essential \
  gcc \
  curl \
  && rm -rf /var/lib/apt/lists/*

# 安装 Node.js 和 npm
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
  apt-get install -y nodejs && \
  npm install -g pm2

# 设置 Python 3.11 为默认版本
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
  update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# 升级 pip
RUN python -m pip install --upgrade pip

# 先复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建日志目录
RUN mkdir -p logs

# 复制项目文件
COPY . .

# 设置环境变量
ENV PORT=8001
ENV HOST=0.0.0.0
ENV NODE_ENV=production

# 暴露端口
EXPOSE 8001

# 使用 PM2 启动服务
CMD ["pm2-runtime", "process_manager/ecosystem.config.js"] 