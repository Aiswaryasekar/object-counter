.DEFAULT_GOAL := help
PYTHON ?= python3
VENV   := .venv
BIN    := $(VENV)/bin
export PYTHONPATH := .

.PHONY: help install model up down logs run run-prod test clean

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-10s %s\n", $$1, $$2}'

$(BIN)/activate: requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install -r requirements.txt
	@touch $(BIN)/activate

install: $(BIN)/activate ## Create virtualenv and install dependencies

model: ## Download the detection model into tmp/model
	./scripts/download_model.sh

up: model ## Start TF Serving, MongoDB and PostgreSQL in Docker
	docker compose up -d

down: ## Stop all containers
	docker compose down

logs: ## Tail container logs
	docker compose logs -f

run: install ## Run the API with fakes (no Docker needed)
	$(BIN)/python -m counter.entrypoints.webapp

run-prod: install ## Run the API against the real services (run `make up` first)
	ENV=prod $(BIN)/python -m counter.entrypoints.webapp

test: install ## Run the test suite
	$(BIN)/pytest

clean: ## Remove venv, caches and debug images
	rm -rf $(VENV) .pytest_cache tmp/debug
	find . -name __pycache__ -type d -prune -exec rm -rf {} +