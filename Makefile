.PHONY: help install generate migrate dbpush dev run test lint format \
        docker-build docker-up docker-down docker-logs docker-migrate clean

PORT ?= 8000

help:
	@echo "Available commands:"
	@echo "  make install        install python deps"
	@echo "  make generate       prisma generate"
	@echo "  make migrate        prisma migrate deploy"
	@echo "  make dbpush         prisma db push"
	@echo "  make dev            run locally with reload"
	@echo "  make run            run (used as container CMD)"
	@echo "  make test"
	@echo "  make lint"
	@echo "  make format"
	@echo "  make docker-build"
	@echo "  make docker-up"
	@echo "  make docker-down"
	@echo "  make docker-migrate run migrations inside the running api container"

install:
	pip install -r requirements.txt

generate:
	prisma generate

migrate:
	prisma migrate deploy

dbpush:
	prisma db push

run: generate
	uvicorn app.main:app --host 0.0.0.0 --port $(PORT)

dev: generate
	uvicorn app.main:app --reload --host 127.0.0.1 --port $(PORT)

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-migrate:
	docker compose exec api make migrate

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +