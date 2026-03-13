# Build stage
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies first (cached layer — only rebuilds when lockfile changes)
COPY uv.lock pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

# Copy source and install project
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Runtime stage — no uv, no build tools
FROM python:3.12-slim
RUN groupadd -g 1001 app && useradd -u 1001 -g app -m -s /bin/false app
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"
COPY --from=build --chown=app:app /app .
USER app
EXPOSE 8000 8765
CMD ["uvicorn", "src.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
