FROM node:20-bookworm AS frontend_builder

WORKDIR /app
COPY . .
RUN set -e; \
    if [ -f package.json ]; then FRONTEND_DIR="."; FRONTEND_ENABLED="true"; \
    elif [ -f frontend/package.json ]; then FRONTEND_DIR="frontend"; FRONTEND_ENABLED="true"; \
    elif [ -f client/package.json ]; then FRONTEND_DIR="client"; FRONTEND_ENABLED="true"; \
    elif [ -f web/package.json ]; then FRONTEND_DIR="web"; FRONTEND_ENABLED="true"; \
    elif [ -f app/package.json ]; then FRONTEND_DIR="app"; FRONTEND_ENABLED="true"; \
    elif [ -f ui/package.json ]; then FRONTEND_DIR="ui"; FRONTEND_ENABLED="true"; \
    else FRONTEND_DIR="."; FRONTEND_ENABLED="false"; fi; \
    rm -rf /tmp/frontend_build && mkdir -p /tmp/frontend_build; \
    if [ "$FRONTEND_ENABLED" = "true" ]; then \
      cd "/app/${FRONTEND_DIR}"; \
      if [ -f package-lock.json ]; then echo "Using npm ci"; npm ci; \
      else echo "No package-lock.json -> using npm install"; npm install; fi; \
      npm run build; \
      if [ -d dist ]; then BUILD_ROOT="dist"; \
      elif [ -d build ]; then BUILD_ROOT="build"; \
      else echo "No build output (dist/build) found" && ls -la && exit 1; fi; \
      INDEX_PATH="$(find "$BUILD_ROOT" -maxdepth 6 -type f -name index.html | head -n 1)"; \
      if [ -z "$INDEX_PATH" ]; then echo "index.html not found" && find "$BUILD_ROOT" -maxdepth 6 -type f && exit 1; fi; \
      INDEX_DIR="$(dirname "$INDEX_PATH")"; \
      cp -r "$INDEX_DIR/." /tmp/frontend_build/; \
      test -f /tmp/frontend_build/index.html; \
    else \
      echo "No frontend package.json found; skipping frontend build."; \
      echo "frontend skipped" > /tmp/frontend_build/.frontend_skipped; \
    fi

FROM python:3.12-slim AS backend

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app/backend"
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY --from=frontend_builder /tmp/frontend_build /app/backend/static
RUN if [ -f backend/static/.frontend_skipped ]; then \
      echo "Frontend build skipped; backend/static/index.html not required."; \
    else \
      test -f backend/static/index.html; \
    fi

EXPOSE 8000
CMD ["sh","-c","uvicorn backend.api.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
