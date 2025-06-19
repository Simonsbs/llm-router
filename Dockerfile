# ─── Stage 1: Builder ──────────────────────────────────────────────
FROM python:3.13-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install Python deps (cached pip)
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# ─── Stage 2: Final runtime ────────────────────────────────────────
FROM python:3.13-slim-bookworm AS final

WORKDIR /app

# Copy dependencies and source from builder
COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app

# Use non-root user for better security
USER nobody
EXPOSE 8080

# Start using uvicorn
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
