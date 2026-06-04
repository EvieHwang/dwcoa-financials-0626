# Multi-stage build: build the frontend, then assemble the backend image that
# serves the built assets. One deployable, no separate origin.

# --- Stage 1: build the React frontend ---
FROM node:22-slim AS frontend
WORKDIR /frontend
# Use the pnpm version pinned in package.json's "packageManager" field, not
# corepack's latest (which enforces a 24h minimum-release-age supply-chain gate
# that rejects fast-moving transitive deps and breaks reproducible builds).
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
COPY frontend/package.json frontend/pnpm-lock.yaml* ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

# --- Stage 2: backend runtime ---
FROM python:3.11-slim AS backend
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STATIC_DIR=/app/static \
    DATABASE_PATH=/data/dwcoa.db

COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --no-cache-dir .

# Bundle the built frontend assets the backend serves.
COPY --from=frontend /frontend/dist ./static

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
