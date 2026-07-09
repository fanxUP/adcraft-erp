# ── 构建阶段：安装编译依赖 + pip install ──────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# 接收 docker-compose.yml 传入的代理设置（用于国内加速构建）
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ENV HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY} \
    NO_PROXY=${NO_PROXY}

# 清华 APT 镜像源 + 编译依赖（代理优先，镜像源兜底）
RUN sed -i 's|http://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# 先只复制依赖声明文件（利用 Docker 层缓存：代码变但依赖不变时无需重新安装）
COPY pyproject.toml .
# 创建一个最小 app 骨架让 pip 能解析包名（--no-editable 不需要完整的 app 代码）
RUN mkdir -p app && touch app/__init__.py

# pip 安装依赖（阿里云镜像加速；gcc 仅在编译 bcrypt/asyncpg 时需要）
RUN pip install \
    -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com \
    --no-cache-dir .

# ── 运行阶段：最小镜像，不含编译工具 ─────────────────────────
FROM python:3.12-slim

WORKDIR /app

# 从 builder 复制已安装的包和 CLI 入口
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin /usr/local/bin/

# 复制源代码和资源文件
COPY pyproject.toml .
COPY app/ app/
COPY alembic.ini .
COPY alembic/ alembic/
COPY scripts/ scripts/

RUN mkdir -p /app/uploads /app/logs

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python scripts/init_app.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
