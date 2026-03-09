# Consolidated Dockerfile for Optifiner Python Services
# Use targets (api, worker) to build specific services

# --- Base Stage ---
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- API Stage ---
FROM base AS api
WORKDIR /app
COPY apps/api/pyproject.toml ./
RUN pip install --no-cache-dir -e . || pip install --no-cache-dir \
    "fastapi>=0.109.0" \
    "uvicorn[standard]>=0.27.0" \
    "pydantic>=2.0.0" \
    "pydantic-settings>=2.1.0" \
    "httpx>=0.27.0" \
    "redis>=5.0.0" \
    "gitpython>=3.1.0" \
    "pygithub>=2.1.0" \
    "sqlalchemy>=2.0.0" \
    "psycopg2-binary>=2.9.9" \
    "alembic>=1.13.0" \
    "python-multipart>=0.0.6"

COPY apps/api/src ./src
RUN pip install --no-cache-dir -e .
EXPOSE 8000
CMD ["python", "-m", "optifiner_api"]

# --- Worker Stage ---
FROM base AS worker
RUN apt-get update && apt-get install -y --no-install-recommends \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash worker
RUN mkdir -p /workspace && chown worker:worker /workspace
RUN mkdir -p /evaluator && chown worker:worker /evaluator

WORKDIR /worker
COPY services/worker/pyproject.toml ./
COPY services/worker/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt || pip install --no-cache-dir \
    "langgraph>=0.2.0" \
    "langchain>=0.3.0" \
    "langchain-anthropic>=0.3.0" \
    "langchain-google-genai>=2.0.0" \
    "langchain-openai>=0.2.0" \
    "pydantic>=2.0.0" \
    "pydantic-settings>=2.0.0" \
    "redis>=5.0.0" \
    "gitpython>=3.1.0" \
    "aiofiles>=24.0.0" \
    "httpx>=0.27.0" \
    "rich>=13.0.0" \
    "click>=8.0.0"

COPY services/worker/src ./src
COPY services/worker/README.md ./
RUN pip install --no-cache-dir -e .
USER worker
ENV WORKSPACE_ROOT=/workspace
ENV PYTHONPATH=/worker/src
CMD ["python", "-m", "worker.docker_entrypoint"]

# --- Web Stage ---
FROM node:20-slim AS web
WORKDIR /app
COPY apps/web/package.json ./
# Using npm install as pnpm might not be in the base image
RUN npm install
COPY apps/web ./
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
