.PHONY: install dev test lint run docker clean

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements-dev.txt

test:
	pytest -v --cov=src --cov-report=term-missing

lint:
	ruff check src tests
	ruff format --check src tests

fmt:
	ruff format src tests

run:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

docker:
	docker compose up --build -d

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__ src/__pycache__ tests/__pycache__ .coverage htmlcov
