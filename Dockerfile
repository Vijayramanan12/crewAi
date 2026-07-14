FROM python:3.13-slim AS builder
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache --no-install-project

COPY . .

RUN uv sync --frozen --no-cache --no-editable

ENV PATH="/app/.venv/bin:$PATH"

CMD ["uv", "run", "crewai", "run"]