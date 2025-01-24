FROM python:3.12
WORKDIR /app

# Install dependencies first
RUN pip install --no-cache-dir pipx
ENV PATH="$PATH:/root/.local/bin"
RUN pipx install "pdm"
COPY pdm.lock pyproject.toml ./
RUN pdm install

COPY . .
EXPOSE 8000
ENTRYPOINT ["uvicorn", "--host=0.0.0.0", "--port=8000", "--reload", "--timeout-graceful-shutdown=0"]
CMD ["main:app"]
