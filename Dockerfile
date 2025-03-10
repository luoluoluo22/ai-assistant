FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖和编译工具
RUN apt-get update && apt-get install -y \
  build-essential \
  python3-dev \
  gcc \
  curl \
  && rm -rf /var/lib/apt/lists/*

# 复制requirements.txt
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制其余项目文件
COPY . .

# 设置环境变量
ENV PORT=8001
ENV HOST=0.0.0.0

# 暴露端口
EXPOSE 8001

# 启动命令
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"] 