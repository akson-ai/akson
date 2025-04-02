FROM python:3.12 AS base

# Install dependencies first
FROM base AS builder
COPY --from=ghcr.io/astral-sh/uv:0.6.2 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY uv.lock pyproject.toml .
RUN uv sync --frozen --no-install-project --no-dev
COPY . .
RUN uv sync --frozen --no-dev

FROM base
WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
ENTRYPOINT ["uvicorn", "--host=0.0.0.0", "--port=8000", "--reload", "--timeout-graceful-shutdown=0"]
CMD ["main:app"]
