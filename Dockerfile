FROM node:20-bookworm AS frontend_builder

WORKDIR /app
COPY . .
RUN set -e; \
    if [ -f package.json ]; then FRONTEND_DIR="."; \
    elif [ -f frontend/package.json ]; then FRONTEND_DIR="frontend"; \
    elif [ -f client/package.json ]; then FRONTEND_DIR="client"; \
    elif [ -f web/package.json ]; then FRONTEND_DIR="web"; \
    elif [ -f app/package.json ]; then FRONTEND_DIR="app"; \
    elif [ -f ui/package.json ]; then FRONTEND_DIR="ui"; \
    else echo "No frontend package.json found" && ls -la && exit 1; fi; \
    cd "/app/${FRONTEND_DIR}"; \
    if [ -f package-lock.json ]; then echo "Using npm ci"; npm ci; \
    else echo "No package-lock.json -> using npm install"; npm install; fi; \
    npm run build; \
    rm -rf /tmp/frontend_build && mkdir -p /tmp/frontend_build; \
    if [ -d dist ]; then cp -r dist/* /tmp/frontend_build/; \
    elif [ -d build ]; then cp -r build/* /tmp/frontend_build/; \
    else echo "No build output (dist/build) found" && ls -la && exit 1; fi; \
    test -f /tmp/frontend_build/index.html

FROM python:3.12-slim AS backend

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app/backend"
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY --from=frontend_builder /tmp/frontend_build /app/backend/static
RUN test -f backend/static/index.html

EXPOSE 8000
CMD ["sh","-c","uvicorn backend.api.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
