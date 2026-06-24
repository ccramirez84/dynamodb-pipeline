.PHONY: help install test test-cov lint format localstack-up localstack-down tf-init tf-plan tf-apply tf-destroy extract-data ingest clean

help:
	@echo "Comandos disponibles:"
	@echo "  make install         - Instala dependencias Python"
	@echo "  make localstack-up   - Levanta LocalStack en Docker"
	@echo "  make localstack-down - Detiene LocalStack"
	@echo "  make tf-init          - terraform init en infra/"
	@echo "  make tf-plan          - terraform plan en infra/"
	@echo "  make tf-apply         - terraform apply en infra/ (crea recursos en LocalStack)"
	@echo "  make tf-destroy       - terraform destroy en infra/"
	@echo "  make extract-data     - Regenera el JSON de productos desde el SQL de Sakila"
	@echo "  make ingest           - Corre el pipeline de ingesta contra LocalStack"
	@echo "  make test             - Corre los tests (mockeados con moto, no requiere LocalStack)"
	@echo "  make test-cov         - Corre los tests con reporte de cobertura"
	@echo "  make lint             - Corre ruff + black --check"
	@echo "  make format           - Formatea el código con black"

install:
	pip install -r requirements.txt --break-system-packages

localstack-up:
	docker run -d --name localstack -p 4566:4566 \
		-e SERVICES=dynamodb,s3,iam,sts \
		localstack/localstack:latest

localstack-down:
	docker stop localstack && docker rm localstack

tf-init:
	cd infra && terraform init

tf-plan:
	cd infra && terraform plan

tf-apply:
	cd infra && terraform apply -auto-approve

tf-destroy:
	cd infra && terraform destroy -auto-approve

extract-data:
	python3 scripts_setup/extract_sakila_to_json.py

ingest:
	python3 -m src.main --file data/processed/product_catalog.json

test:
	python3 -m pytest tests/ -v

test-cov:
	python3 -m pytest tests/ -v --cov=src --cov-report=term-missing

lint:
	ruff check src/ tests/
	black --check src/ tests/

format:
	black src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .coverage
