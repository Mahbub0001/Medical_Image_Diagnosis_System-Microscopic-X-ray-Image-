# ─────────────────────────────────────────────────────────────────
# BioLens Backend Dockerfile
# FastAPI + PyTorch (CPU) + Uvicorn
# ─────────────────────────────────────────────────────────────────

# ── Stage 1: Builder ─────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps needed to compile some Python packages (psycopg2, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install into a prefix directory so we can
# copy only the installed libs into the final image (keeps it lean)
COPY requirements.txt .

# PyTorch CPU-only build — much smaller than the default CUDA wheel
RUN pip install --no-cache-dir --prefix=/install \
    -r requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu


# ── Stage 2: Runtime ─────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="Mahbub Ul Alam Bhuiyan & Mahir Ahamed Rohan"
LABEL description="BioLens Backend — HemaFusion FastAPI Inference Server"

WORKDIR /app

# Runtime-only system libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source
COPY app/ ./app/
COPY requirements.txt .

# Create necessary runtime directories (uploads, reports, heatmaps, models)
RUN mkdir -p uploads reports heatmaps models

# Non-root user for security
RUN useradd -m -u 1001 biolens && chown -R biolens:biolens /app
USER biolens

# Expose FastAPI port
EXPOSE 10000

# Health check — confirms the API is responsive
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/ || exit 1

# Start uvicorn; PORT env variable is set by Render / docker-compose
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
