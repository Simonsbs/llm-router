# Makefile

# ───────────────────────────────────────────────────────────────────────────────
# Build automation script for the SimonGPT LLM Router.
#
# This Makefile supports:
# - Docker image build and run
# - K8s-style health probe definitions (via YAML embedding)
#
# Usage:
#   make build         → Build the Docker image
#   make run           → Run the image locally with env vars
#
# You must have Docker and Make installed to use this file.
# Windows users can run this from Git Bash or WSL.
# ───────────────────────────────────────────────────────────────────────────────

IMAGE_NAME = simongpt/llm-router
TAG        = latest

.PHONY: build run

# ────── Build the Docker image ──────
build:
	docker build -t $(IMAGE_NAME):$(TAG) .

# ────── Run the image locally ──────
run:
	docker run --rm -p 8000:8000 \
	  -e LLM_ROUTER_API_KEY=$$LLM_ROUTER_API_KEY \
	  $(IMAGE_NAME):$(TAG)

# ────── Kubernetes health probes ──────
# These are not actual targets but serve as embedded reference for K8s configs.
# You can copy-paste them into a pod spec or Helm chart as needed.

livenessProbe:
  httpGet:
    path: /healthz         # basic service health check
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 15

readinessProbe:
  httpGet:
    path: /readyz          # verifies LLMs are reachable
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 10
