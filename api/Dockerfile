FROM python:3.12 AS base
COPY --from=ghcr.io/astral-sh/uv:0.6.17 /uv /uvx /bin/

# Install npm for running MCP servers written in Javascript
RUN apt-get update && apt-get install -y docker.io npm

# Install dependencies first
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project
ENV PATH="/app/.venv/bin:$PATH"

COPY . /app
EXPOSE 8000
VOLUME "/root/.cache/uv" "/root/.npm"
ENTRYPOINT ["uvicorn", "--host=0.0.0.0", "--port=8000", "--reload", "--timeout-graceful-shutdown=0"]
CMD ["main:app"]
