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
    echo "FRONTEND_DIR=${FRONTEND_DIR}" > /tmp/frontend_dir.env; \
    echo "FRONTEND_DIR=${FRONTEND_DIR}"; \
    ls -la /app; \
    ls -la "/app/${FRONTEND_DIR}" || true
RUN . /tmp/frontend_dir.env; cd "/app/$FRONTEND_DIR" && pwd && ls -la && node -v && npm -v
RUN . /tmp/frontend_dir.env; cd "/app/$FRONTEND_DIR" && cat package.json | head -n 40
RUN . /tmp/frontend_dir.env; cd "/app/$FRONTEND_DIR" && \
    if [ -f package-lock.json ]; then echo "Using npm ci"; npm ci; \
    else echo "No package-lock.json -> using npm install"; npm install; fi
RUN . /tmp/frontend_dir.env; cd "/app/$FRONTEND_DIR" && npm run build
RUN . /tmp/frontend_dir.env; cd "/app/$FRONTEND_DIR" && \
    echo "Listing build outputs:" && ls -la && \
    if [ -d dist ]; then echo "Found dist"; rm -rf /tmp/frontend_build && cp -r dist /tmp/frontend_build; \
    elif [ -d build ]; then echo "Found build"; rm -rf /tmp/frontend_build && cp -r build /tmp/frontend_build; \
    else echo "No build output (dist/build) found"; echo "Tree:"; ls -la; exit 1; fi && \
    echo "Copied to /tmp/frontend_build:" && ls -la /tmp/frontend_build

FROM python:3.12-slim AS backend

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY --from=frontend_builder /tmp/frontend_build /app/backend/static

EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.api.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
