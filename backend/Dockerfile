# Backend-only Dockerfile (dev local / deploy separado)
# Para deploy unificado (Render Web Service), usa el Dockerfile en la raíz del repo.
#
# Build context: ./backend
# Uso local: docker build -f backend/Dockerfile -t laliga-backend ./backend

# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install UV
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Create virtual environment and install dependencies
RUN uv venv --python 3.11 && \
    . .venv/bin/activate && \
    uv pip install --no-cache -r pyproject.toml


# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/ ./src/
COPY models/ ./models/
COPY data/ ./data/

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Expose port
EXPOSE 8000

# Run API
CMD ["uvicorn", "src.laliga_predictor.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
