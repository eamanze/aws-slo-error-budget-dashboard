.DEFAULT_GOAL := help

.PHONY: help setup up down test lint validate load-test fault-errors fault-latency fault-clear incident clean

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "%-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Create local environment configuration
	@test -f .env || cp .env.example .env

up: setup ## Build and start the local stack
	docker compose up --build --detach

down: ## Stop the local stack
	docker compose down

test: ## Run application tests in an isolated container
	docker run --rm -v "$(CURDIR):/work" -w /work python:3.12.11-slim-bookworm sh -c 'pip install -q -r app/requirements.txt pytest==8.4.1 pytest-cov==6.2.1 && pytest --cov=app --cov-fail-under=85 -q app/tests'

lint: ## Lint Python source
	docker run --rm -v "$(CURDIR):/work" -w /work python:3.12.11-slim sh -c 'pip install -q ruff==0.12.4 && ruff check app incident load-tests'

validate: ## Validate Compose, Prometheus rules, dashboard JSON, and Terraform formatting
	docker compose config --quiet
	docker run --rm --entrypoint promtool -v "$(CURDIR)/monitoring/prometheus:/etc/prometheus:ro" prom/prometheus:v3.5.0 check config /etc/prometheus/prometheus.yml
	python3 -m json.tool monitoring/grafana/dashboards/slo-dashboard.json >/dev/null
	terraform fmt -check -recursive terraform

load-test: ## Generate successful application traffic
	python3 load-tests/load.py

fault-errors: ## Inject deterministic HTTP failures
	./scripts/fault.sh errors

fault-latency: ## Inject 750ms latency
	./scripts/fault.sh latency

fault-clear: ## Remove all injected faults
	./scripts/fault.sh clear

incident: ## Run a short, automated failure exercise
	./scripts/run-incident.sh

clean: down ## Remove local named volumes (destructive to local metrics)
	docker compose down --volumes
