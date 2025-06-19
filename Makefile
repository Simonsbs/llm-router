IMAGE_NAME = simongpt/llm-router
TAG        = latest

.PHONY: build run

build:
	docker build -t $(IMAGE_NAME):$(TAG) .

run:
	docker run --rm -p 8000:8000 \
	  -e LLM_ROUTER_API_KEY=$$LLM_ROUTER_API_KEY \
	  $(IMAGE_NAME):$(TAG)
