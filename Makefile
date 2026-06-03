.PHONY: help up down logs build migrate revision test-backend test-frontend test-worker lint clean

help:
	@echo "ShopGuard development commands"
	@echo ""
	@echo "  make up              Start all services (docker compose)"
	@echo "  make down            Stop all services"
	@echo "  make logs            Tail logs from all services"
	@echo "  make build           Rebuild all images"
	@echo "  make migrate         Run Alembic migrations against MySQL"
	@echo "  make revision m='msg' Create new Alembic revision"
	@echo "  make test-backend    Run backend case suite  (tests/test_be.py)"
	@echo "  make test-frontend   Run frontend case suite (test_fe_*)"
	@echo "  make test-worker     Run AI-worker case suite (tests/test_wk.py)"
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

# Consolidated per-layer case suites (mapped to docs/*_test_cases.csv).
# Tests NOT covered by these targets are run explicitly:
#   Backend smoke    : docker compose exec backend pytest tests/test_smoke.py -v
#   Backend mutation : docker compose exec backend pytest tests/test_mutation_lockout.py -v
#   Backend (all)    : docker compose exec backend pytest -v
#   Rate limit (Redis): docker compose exec backend pytest tests/test_be.py -k "tc36 or tc37"
test-backend:
	docker compose exec backend pytest tests/test_be.py -v

test-frontend:
	docker compose exec frontend npm test -- test_fe

test-worker:
	docker compose exec ai-worker python -m pytest tests/test_wk.py -v

lint:
	docker compose exec backend ruff check app/
	docker compose exec frontend npm run lint

clean:
	docker compose down -v
	rm -rf backend/__pycache__ ai-worker/__pycache__ frontend/.next frontend/node_modules
