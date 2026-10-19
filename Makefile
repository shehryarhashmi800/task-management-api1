.PHONY: up down logs migrate test build lint format audit coverage

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api

migrate:
	docker compose exec api alembic upgrade head

test:
	docker compose --profile test run --rm --build test

build:
	docker compose build

lint:
	ruff check .
	ruff format --check .
	vulture app --min-confidence 80 --ignore-names cls,attrs

format:
	ruff format .
	ruff check --fix .

audit:
	pip-audit -r requirements.txt

coverage:
	pytest --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=85
