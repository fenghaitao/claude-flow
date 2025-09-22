# Multi-stage Dockerfile for Claude-Flow
# Optimized for production deployment with minimal attack surface

# ==============================================================================
# Stage 1: Base Python environment with system dependencies
# ==============================================================================
FROM python:3.11-slim-bullseye as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gcc \
    g++ \
    git \
    libffi-dev \
    libpq-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 claudeflow \
    && useradd --uid 1000 --gid claudeflow --shell /bin/bash --create-home claudeflow

# Set up application directory
WORKDIR /app
RUN chown -R claudeflow:claudeflow /app

# ==============================================================================
# Stage 2: Dependencies installation
# ==============================================================================
FROM base as dependencies

# Copy requirements files
COPY requirements.txt requirements-test.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Install optional dependencies for production
RUN pip install --no-cache-dir \
    gunicorn \
    uvloop \
    httptools

# ==============================================================================
# Stage 3: Development image (includes test dependencies)
# ==============================================================================
FROM dependencies as development

# Install test dependencies
RUN pip install --no-cache-dir -r requirements-test.txt

# Install development tools
RUN pip install --no-cache-dir \
    pytest-cov \
    pytest-xdist \
    pre-commit \
    jupyter

# Copy source code
COPY --chown=claudeflow:claudeflow . .

# Switch to non-root user
USER claudeflow

# Set Python path
ENV PYTHONPATH=/app/src

# Default command for development
CMD ["python", "-m", "claude_flow.cli.main", "server", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ==============================================================================
# Stage 4: Production image (minimal, security-hardened)
# ==============================================================================
FROM dependencies as production

# Remove build dependencies to reduce attack surface
RUN apt-get update && apt-get remove -y \
    build-essential \
    gcc \
    g++ \
    git \
    pkg-config \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /root/.cache

# Copy only source code (no tests, docs, etc.)
COPY --chown=claudeflow:claudeflow src/ ./src/
COPY --chown=claudeflow:claudeflow config/ ./config/
COPY --chown=claudeflow:claudeflow scripts/ ./scripts/
COPY --chown=claudeflow:claudeflow LICENSE README.md ./

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/tmp \
    && chown -R claudeflow:claudeflow /app/logs /app/data /app/tmp

# Switch to non-root user
USER claudeflow

# Set Python path
ENV PYTHONPATH=/app/src

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Production command
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--worker-connections", "1000", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--timeout", "30", \
     "--keep-alive", "5", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "claude_flow.api.server:app"]

# ==============================================================================
# Stage 5: AI Worker image (optimized for ML workloads)
# ==============================================================================
FROM nvidia/cuda:11.8-runtime-ubuntu20.04 as ai-worker

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    CUDA_VISIBLE_DEVICES=all

# Install Python and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3.11-distutils \
    python3-pip \
    build-essential \
    curl \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create symlinks for python
RUN ln -s /usr/bin/python3.11 /usr/bin/python \
    && ln -s /usr/bin/python3.11 /usr/bin/python3

# Create non-root user
RUN groupadd --gid 1000 claudeflow \
    && useradd --uid 1000 --gid claudeflow --shell /bin/bash --create-home claudeflow

# Set up application directory
WORKDIR /app
RUN chown -R claudeflow:claudeflow /app

# Install Python dependencies with CUDA support
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Install PyTorch with CUDA support
RUN pip install --no-cache-dir \
    torch==2.0.1+cu118 \
    torchvision==0.15.2+cu118 \
    torchaudio==2.0.2+cu118 \
    --index-url https://download.pytorch.org/whl/cu118

# Install additional ML dependencies
RUN pip install --no-cache-dir \
    accelerate \
    bitsandbytes \
    datasets \
    evaluate \
    optimum

# Copy source code
COPY --chown=claudeflow:claudeflow src/ ./src/
COPY --chown=claudeflow:claudeflow config/ ./config/

# Create necessary directories
RUN mkdir -p /app/models /app/cache /app/logs \
    && chown -R claudeflow:claudeflow /app/models /app/cache /app/logs

# Switch to non-root user
USER claudeflow

# Set Python path
ENV PYTHONPATH=/app/src

# Set model cache directory
ENV TRANSFORMERS_CACHE=/app/cache/transformers
ENV HF_HOME=/app/cache/huggingface

# Expose port
EXPOSE 8001

# AI Worker command
CMD ["python", "-m", "claude_flow.neural.worker", "--port", "8001"]

# ==============================================================================
# Stage 6: Monitoring image (includes observability tools)
# ==============================================================================
FROM production as monitoring

# Switch back to root to install monitoring tools
USER root

# Install monitoring dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    prometheus-node-exporter \
    && rm -rf /var/lib/apt/lists/*

# Install additional monitoring Python packages
RUN pip install --no-cache-dir \
    prometheus-client \
    jaeger-client \
    opentelemetry-distro \
    opentelemetry-exporter-jaeger \
    opentelemetry-exporter-prometheus

# Copy monitoring configuration
COPY --chown=claudeflow:claudeflow config/observability.example.yaml ./config/observability.yaml

# Switch back to non-root user
USER claudeflow

# Expose monitoring ports
EXPOSE 8000 9090 9100

# Monitoring command
CMD ["python", "-m", "claude_flow.monitoring.server", "--enable-all"]

# ==============================================================================
# Metadata and labels
# ==============================================================================
LABEL org.opencontainers.image.title="Claude-Flow" \
      org.opencontainers.image.description="Enterprise AI Agent Orchestration Platform" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.vendor="Claude-Flow Project" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/claude-flow/python-claude-flow" \
      org.opencontainers.image.documentation="https://claude-flow.readthedocs.io" \
      maintainer="Claude-Flow Team <team@claude-flow.io>"

# Build arguments for customization
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL org.opencontainers.image.created=$BUILD_DATE \
      org.opencontainers.image.revision=$VCS_REF \
      org.opencontainers.image.version=$VERSION