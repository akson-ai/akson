FROM python:3.12 AS base
COPY --from=ghcr.io/astral-sh/uv:0.6.17 /uv /bin/

# Install dependencies first
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project
ENV PATH="/app/.venv/bin:$PATH"

COPY . /app
ENTRYPOINT ["uv", "run"]
CMD ["main.py"]
