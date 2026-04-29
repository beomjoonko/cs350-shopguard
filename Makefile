.PHONY: help up down logs build migrate revision test-backend test-frontend lint clean

help:
	@echo "ShopGuard development commands"
	@echo ""
	@echo "  make up              Start all services (docker compose)"
	@echo "  make down            Stop all services"
	@echo "  make logs            Tail logs from all services"
	@echo "  make build           Rebuild all images"
	@echo "  make migrate         Run Alembic migrations against MySQL"
	@echo "  make revision m='msg' Create new Alembic revision"
	@echo "  make test-backend    Run backend pytest"
	@echo "  make test-frontend   Run frontend tests"
	@echo "  make lint            Run linters (ruff + eslint)"
	@echo "  make clean           Remove volumes and build artifacts"

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

migrate:
	docker compose exec backend alembic upgrade head

revision:
	docker compose exec backend alembic revision --autogenerate -m "$(m)"

test-backend:
	docker compose exec backend pytest -v

test-frontend:
	docker compose exec frontend npm test

lint:
	docker compose exec backend ruff check app/
	docker compose exec frontend npm run lint

clean:
	docker compose down -v
	rm -rf backend/__pycache__ ai-worker/__pycache__ frontend/.next frontend/node_modules
