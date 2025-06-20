# SimonGPT LLM Router

**Author:** Simon B. Stirling  
**Project:** SimonGPT – Persona-aware LLM Router & Embedding Service

## Overview

The `llm-router` is a FastAPI-based microservice that acts as a dynamic router between clients and multiple Large Language Model providers like **OpenAI**, **Ollama**, and **DeepSeek**. It is a core component of the SimonGPT ecosystem, built to intelligently route requests based on input types, performance constraints, or user preferences.

It supports:

- Standard and streaming chat completions
- Embedding generation
- JWT-authenticated rate-limited API access
- Centralized request logging, metrics, and observability

---

## 🔧 Architecture

The router is composed of the following major components:

### 1. `main.py`

The central entrypoint for the FastAPI app. Defines:

- Endpoints (`/v1/chat/completions`, `/v1/embeddings`, `/v1/token`, `/healthz`, `/readyz`)
- Middleware: CORS, correlation ID, logging, body size limits, CSP headers
- Rate limiting (SlowAPI)
- Prometheus instrumentation

### 2. `config.py`

Manages runtime environment variables using Pydantic. Ensures safe defaults and centralizes:

- Secrets (JWT, API key)
- LLM model selection defaults
- CORS origins
- Rate limiting strings

### 3. `schemas.py`

Validates request payloads. Enforces:

- Message length caps
- Token limits
- Proper message format

### 4. `adapters/`

Pluggable, provider-specific adapter modules that implement:

- `chat()` – non-streaming completions
- `chat_stream()` – SSE streaming responses
- `embed()` – text embeddings

Base interface in `base.py`, routing entrypoint in `adapter.py`, provider implementations are lazily imported using Python reflection.

### 5. `runnables.py`

Creates `RunnableLambda` chains per provider, making this router LangChain-compatible.

### 6. Middleware Modules

- `LoggingMiddleware`: request/response metrics with request ID
- `SecurityHeadersMiddleware`: CSP enforcement
- `BodySizeLimitMiddleware`: 413 rejection for oversized payloads

### 7. `exceptions.py`

Custom error handler (`AdapterError`) with integrated FastAPI exception routing.

---

## 🧠 Design Principles

- **Multi-provider LLM support** with hot-swappable adapters
- **Streaming support** via SSE
- **Rate limiting** for each endpoint class
- **Environment-first config** with fallback values
- **Minimal external dependencies**, production-ready from the ground up

---

## 🔐 Security & Access

- JWT tokens are issued via `/v1/token` using a master API key.
- All inference endpoints require bearer token validation (`Authorization: Bearer <token>`).
- Payloads over 1MB are automatically rejected.

---

## 📊 Observability

- Prometheus `/metrics` endpoint with support for multi-process mode.
- Per-request JSON logs with correlation IDs for distributed tracing.

---

## 🧪 Health Checks

- `/healthz`: confirms app is running (liveness probe)
- `/readyz`: verifies connectivity to all required LLM providers (readiness probe)

---

## 📂 File Structure

```plaintext
app/
├── adapters/                # Modular providers: OpenAI, Ollama, DeepSeek, etc.
│   ├── adapter.py           # Runtime adapter loader and router
│   ├── base.py              # Common adapter interface
│   ├── runnables.py         # LangChain-compatible entrypoint
├── config.py                # Environment config schema
├── dependencies.py          # FastAPI DI layer for adapters
├── exceptions.py            # Central adapter error type
├── logging_config.py        # JSON structured logging setup
├── main.py                  # FastAPI application root
├── middleware_*             # Custom middleware modules
├── middlewares.py           # Logging + correlation tracing middleware
├── route_logic.py           # Determines provider/model selection
├── schemas.py               # Input validation (chat & embedding)
├── security.py              # JWT validation logic
```

---

## 🧑‍💻 Author

**Simon B. Stirling**  
Senior Solution Architect & Technologist  
Builder of intelligent, modular AI pipelines with full-stack mastery.  
[BestDev.co.il](https://bestdev.co.il)

---

## 📜 License

## MIT – Free to use, extend, and repurpose

## 🐳 Deployment

This project supports both **local** and **remote** containerized deployment via:

### `start-llm-router.ps1` (Windows PowerShell)

A robust PowerShell script to build, tag, push, and run the Docker container.

**Features:**

- Parses `.env` file for secrets and settings
- Supports deploying to local Docker or remote SSH target
- Uses `docker buildx` for cross-platform builds
- Automatically cleans up old containers

**Usage:**

```powershell
./start-llm-router.ps1 -Target remote -ApiKey "<your-api-key>" -JwtSecret "<your-secret>"
```

### `Makefile` (Linux/macOS CI or DevOps pipelines)

Simplified local development and build automation.

**Targets:**

- `make build`: Builds the Docker image
- `make run`: Runs the service locally on port 8000
- `make livenessProbe`: Kubernetes-compatible healthcheck config

### `Dockerfile`

Two-stage build to optimize for size and security.

- Stage 1: Installs Python and builds dependencies
- Stage 2: Runs with `nobody` user for security
- `EXPOSE 8080` for container networking
- Entrypoint: `uvicorn app.main:app --host 0.0.0.0 --port 8080`

---

## 🖥️ Example `.env` File

```env
LLM_ROUTER_API_KEY=changeme123
JWT_SECRET_KEY=supersecretjwt
OLLAMA_URL=http://host.docker.internal:11434
```

---

## ✅ Deployment Summary

| Environment  | Method                                        | Port | Auth Required |
| ------------ | --------------------------------------------- | ---- | ------------- |
| Local Dev    | `make run` or PowerShell                      | 8000 | No            |
| Local Docker | `start-llm-router.ps1`                        | 8080 | Yes (JWT)     |
| Remote SSH   | `start-llm-router.ps1 -Target remote`         | 8080 | Yes (JWT)     |
| K8s Ready    | `livenessProbe`, `readinessProbe` in Makefile | 8080 | Yes (JWT)     |
