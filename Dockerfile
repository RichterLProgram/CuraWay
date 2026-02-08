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
    else FRONTEND_DIR="."; FRONTEND_ENABLED="false"; mkdir -p /tmp/frontend_build; fi; \
    echo "FRONTEND_DIR=${FRONTEND_DIR}" > /tmp/frontend_dir.env; \
    echo "FRONTEND_ENABLED=${FRONTEND_ENABLED}" >> /tmp/frontend_dir.env; \
    echo "FRONTEND_DIR=${FRONTEND_DIR}"; \
    echo "FRONTEND_ENABLED=${FRONTEND_ENABLED}"; \
    ls -la /app; \
    ls -la "/app/${FRONTEND_DIR}" || true
RUN . /tmp/frontend_dir.env; if [ "$FRONTEND_ENABLED" = "true" ]; then \
    cd "/app/$FRONTEND_DIR" && pwd && ls -la && node -v && npm -v; \
    else echo "Skipping frontend build (no package.json found)."; fi
RUN . /tmp/frontend_dir.env; if [ "$FRONTEND_ENABLED" = "true" ]; then \
    cd "/app/$FRONTEND_DIR" && cat package.json | head -n 40; \
    else echo "Skipping frontend build (no package.json found)."; fi
RUN . /tmp/frontend_dir.env; if [ "$FRONTEND_ENABLED" = "true" ]; then \
    cd "/app/$FRONTEND_DIR" && \
    if [ -f package-lock.json ]; then echo "Using npm ci"; npm ci; \
    else echo "No package-lock.json -> using npm install"; npm install; fi; \
    else echo "Skipping frontend build (no package.json found)."; fi
RUN . /tmp/frontend_dir.env; if [ "$FRONTEND_ENABLED" = "true" ]; then \
    cd "/app/$FRONTEND_DIR" && npm run build; \
    else echo "Skipping frontend build (no package.json found)."; fi
RUN . /tmp/frontend_dir.env; if [ "$FRONTEND_ENABLED" = "true" ]; then \
    cd "/app/$FRONTEND_DIR" && \
    echo "Listing build outputs:" && ls -la && \
    if [ -d dist ]; then echo "Found dist"; rm -rf /tmp/frontend_build && cp -r dist /tmp/frontend_build; \
    elif [ -d build ]; then echo "Found build"; rm -rf /tmp/frontend_build && cp -r build /tmp/frontend_build; \
    else echo "No build output (dist/build) found"; echo "Tree:"; ls -la; exit 1; fi && \
    echo "Copied to /tmp/frontend_build:" && ls -la /tmp/frontend_build; \
    else echo "Skipping frontend build (no package.json found)."; fi

FROM python:3.12-slim AS backend

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app/backend"
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY --from=frontend_builder /tmp/frontend_build /app/backend/static

EXPOSE 8000
CMD ["sh", "-c", "gunicorn backend.api.server:app --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 8 --timeout 120"]
