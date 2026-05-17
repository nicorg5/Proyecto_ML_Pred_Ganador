# ====== STAGE 1: Build frontend ======
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package.json (and lock if exists)
COPY frontend/package*.json ./

# Install dependencies
RUN npm install --no-audit --no-fund

# Copy frontend source
COPY frontend/index.html ./
COPY frontend/vite.config.js ./
COPY frontend/src ./src

# Build frontend (output: /app/frontend/dist)
RUN npm run build


# ====== STAGE 2: Build Python backend ======
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    postgresql-client \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN pip install --no-cache-dir uv

# Copy backend dependencies
COPY backend/pyproject.toml backend/uv.lock* ./

# Copy README to root (pyproject.toml references "../README.md")
COPY README.md /README.md

# Create virtual environment and install dependencies
RUN uv venv --python 3.11 && \
    . .venv/bin/activate && \
    uv pip install --no-cache -r pyproject.toml

# Copy backend application code
COPY backend/src ./src
COPY backend/models ./models
COPY backend/data ./data

# Copy frontend build from stage 1 to backend's static folder
COPY --from=frontend-builder /app/frontend/dist ./src/laliga_predictor/static

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Expose port (Render injects $PORT, default 8000)
EXPOSE 8000

# Run API (use $PORT for Render compatibility, fallback to 8000)
CMD uvicorn src.laliga_predictor.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
