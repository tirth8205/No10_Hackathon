# Gateway Check: one container serves the API and the built frontend.
# Build:  docker build -t gateway-check .
# Run:    docker run -p 8000:8000 -e OPENAI_API_KEY=... -v gc-data:/data gateway-check
FROM node:22-alpine AS web
WORKDIR /src/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
# antiword reads Word 97 .doc files; everything else is read in Python
RUN apt-get update && apt-get install -y --no-install-recommends antiword && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
COPY --from=web /src/web/dist ./web/dist
RUN mkdir -p /data
ENV GC_DB_PATH=/data/gateway_check.sqlite3 \
    GC_CACHE_DIR=/data/cache \
    GC_CACHE=on \
    GC_LLM=openai \
    PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"
CMD ["sh", "-c", "/app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips=*"]
