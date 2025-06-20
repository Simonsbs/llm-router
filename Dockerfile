# ───────────────────────────────────────────────────────────────────────────────
# Dockerfile for SimonGPT LLM Router
#
# Uses multi-stage builds:
# - Stage 1 ("builder"): Installs Python dependencies in an isolated build layer
# - Stage 2 ("final"): Copies only the installed environment + source code
#
# Benefits:
# - Smaller final image
# - Clean dependency separation
# - No build tools in production container
#
# Exposes port 8080 and runs the FastAPI app via Uvicorn.
# ───────────────────────────────────────────────────────────────────────────────

# ────── Stage 1: Builder ───────────────────────────────────────────────────────
FROM python:3.13-slim-bookworm AS builder

# Set working directory
WORKDIR /app

# Install system packages needed for building some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy only dependency list first (layer cache optimization)
COPY requirements.txt .

# Upgrade pip tools and install all required dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy rest of the app source code
COPY . .

# ────── Stage 2: Final runtime image ───────────────────────────────────────────
FROM python:3.13-slim-bookworm AS final

# Set working directory in runtime container
WORKDIR /app

# Copy only the installed Python environment and source code from the builder
COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app

# Use non-root user for security (limits container privileges)
USER nobody

# Expose FastAPI default port
EXPOSE 8080

# Start server using uvicorn
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
