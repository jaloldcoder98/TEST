.PHONY: up down logs backend-shell migrate seed test-backend test-frontend test-e2e test-bot test

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

# Playwright needs a real browser + the frontend built and running against the backend, so it's
# not part of `docker compose exec frontend npm test` — run it after `make up` (or the frontend
# dev server) is already serving on :3000.
test-e2e:
	docker compose exec frontend npm run test:e2e

test-bot:
	docker compose exec telegram-bot pytest

test: test-backend test-frontend test-bot
