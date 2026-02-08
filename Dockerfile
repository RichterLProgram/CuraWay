FROM node:20-bookworm AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
RUN if [ -d dist ]; then cp -r dist /app/frontend/build_output; \
    elif [ -d build ]; then cp -r build /app/frontend/build_output; \
    else echo "No frontend build output found" && exit 1; fi

FROM python:3.12-slim AS backend

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY --from=frontend-build /app/frontend/build_output backend/static

EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.api.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
