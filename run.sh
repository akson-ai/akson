#!/bin/sh
export ALLOW_ORIGINS="http://localhost:5173"
exec uv run fastapi dev --host 0.0.0.0 --port 8000 --reload
