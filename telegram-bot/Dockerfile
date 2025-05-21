FROM python:3.13 AS base
COPY --from=ghcr.io/astral-sh/uv:0.7.3 /uv /bin/

RUN apt-get update && apt-get install -y \
    flac \
    ffmpeg

# Install dependencies first
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=telegram-bot/uv.lock,target=/app/uv.lock \
    --mount=type=bind,source=telegram-bot/pyproject.toml,target=/app/pyproject.toml \
    --mount=type=bind,source=client/uv.lock,target=/client/uv.lock \
    --mount=type=bind,source=client/pyproject.toml,target=/client/pyproject.toml \
    uv sync --locked --no-install-project \
        --no-install-package akson-client
ENV PATH="/app/.venv/bin:$PATH"

COPY ./client/ /client
COPY ./telegram-bot/ /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=telegram-bot/uv.lock,target=/app/uv.lock \
    --mount=type=bind,source=telegram-bot/pyproject.toml,target=/app/pyproject.toml \
    --mount=type=bind,source=client/uv.lock,target=/client/uv.lock \
    --mount=type=bind,source=client/pyproject.toml,target=/client/pyproject.toml \
    uv sync --locked --no-install-project

ENTRYPOINT ["uv", "run"]
CMD ["main.py"]
