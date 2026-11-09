FROM python:3.9-slim

# 让 Python 输出直接进入容器日志，并避免生成 .pyc 文件
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_DEBUG=0 \
    PORT=5000

WORKDIR /app

# 安装后端依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir flask flask-cors

# 复制后端和前端页面
COPY app.py index.html ./

EXPOSE 5000

# Flask 同时提供 /api/* 接口和 / 前端页面
CMD ["python", "app.py"]
