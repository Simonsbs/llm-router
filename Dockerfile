# ─── Builder stage: compile and install dependencies ─────────────────────
FROM python:3.13-slim-bookworm AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/usr/local -r requirements.txt
COPY . .

# ─── Final stage: minimal Distroless runtime ────────────────────────────
FROM gcr.io/distroless/python3:nonroot
WORKDIR /app
# Copy installed libraries and application code
COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app

# Run as non-root user provided by Distroless
USER nonroot

# Expose the application port and define the startup command
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
