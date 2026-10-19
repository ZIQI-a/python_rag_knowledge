# syntax=docker/dockerfile:1
# Python 版本与项目保持一致；固定 uv 版本以减少构建环境差异。
FROM python:3.14-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_CONCURRENT_DOWNLOADS=2 \
    UV_CONCURRENT_INSTALLS=1 \
    UV_NO_CACHE=1 \
    PATH="/app/backend/.venv/bin:$PATH" \
    HOME=/home/rag

# 使用已在服务器验证的腾讯云 Debian 镜像，保留软件包签名校验。
# 下载连接设置有限重试和超时，避免网络故障时长时间无反馈。
# Python 3.14 下部分依赖需源码编译，build-essential 提供 gcc / g++。
RUN sed -i 's|https\?://deb.debian.org|http://mirrors.cloud.tencent.com|g' /etc/apt/sources.list.d/debian.sources \
    && printf 'Acquire::Retries "3";\nAcquire::http::Timeout "30";\nAcquire::https::Timeout "30";\n' > /etc/apt/apt.conf.d/80rag-network \
    && apt-get update \
    && apt-get install -y --no-install-recommends build-essential ca-certificates libglib2.0-0 libgl1 libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home rag \
    && mkdir -p /home/rag/.cache \
    && chown -R rag:rag /home/rag

# 从 Python 包索引安装同版本 uv，避免额外依赖 GHCR 镜像层下载。
RUN python -m pip install --no-cache-dir --timeout 30 --retries 3 --index-url https://mirrors.cloud.tencent.com/pypi/simple uv==0.12.17

WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./

# 保留锁文件中的普通包版本；GPU 专属依赖不进入无 GPU 的服务器镜像。
# --torch-backend 仅用于 uv pip，运行时不再使用 uv run 自动同步原锁文件。
RUN uv export --frozen --no-dev --no-hashes --no-emit-project --output-file /tmp/requirements.lock.txt \
    && sed -E '/^(nvidia-|cuda-|triton==)/d' /tmp/requirements.lock.txt > /tmp/requirements.cpu.txt \
    && uv venv --python /usr/local/bin/python .venv \
    && uv pip install --python .venv/bin/python --default-index https://mirrors.cloud.tencent.com/pypi/simple --torch-backend cpu -r /tmp/requirements.cpu.txt \
    && uv pip check --python .venv/bin/python \
    && .venv/bin/python -c "import torch; assert torch.version.cuda is None, '必须安装 CPU 版 PyTorch'" \
    && rm /tmp/requirements.lock.txt /tmp/requirements.cpu.txt

COPY backend/ ./
USER rag
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
