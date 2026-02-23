# syntax=docker/dockerfile:1
#
# Qwen3-ASR Wrapper & Streaming Bridge Dockerfile
#
# Lightweight container (no GPU) that serves:
# - Batch wrapper (/transcribe) via providers.qwen3_asr.service
# - Streaming bridge (WebSocket) via providers.qwen3_asr.streaming_bridge
#
# The actual GPU inference runs in a separate vLLM container.

#########################  builder #################################
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Dependency manifest first for cache-friendly installs
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --group qwen3-asr

#########################  runtime #################################
FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl libsndfile1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder's venv to system Python
COPY --from=builder /app/.venv/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Copy application code
COPY common/ ./common/
COPY providers/qwen3_asr/ ./providers/qwen3_asr/

# Default environment variables
ENV QWEN3_VLLM_URL="http://qwen3-asr:8000"
ENV ASR_MODEL="Qwen/Qwen3-ASR-1.7B"

EXPOSE 8765

CMD ["python", "-m", "providers.qwen3_asr.service", "--port", "8765"]
