.PHONY: up down logs backend-shell migrate seed test-backend test-frontend

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

backend-shell:
	docker compose exec backend bash

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python scripts/import_exercises.py
	docker compose exec backend python scripts/seed_database.py

test-backend:
	docker compose exec backend pytest

test-frontend:
	docker compose exec frontend npm test
