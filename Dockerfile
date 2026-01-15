FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    wakeonlan \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml .
COPY tasker_mcp/ tasker_mcp/

RUN uv pip install --system .

EXPOSE 8100

CMD ["tasker-mcp", "--transport", "sse", "--port", "8100"]
