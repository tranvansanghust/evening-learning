ENV_FILE := ./backend/.env
DC := docker compose --env-file $(ENV_FILE)

.PHONY: up down build logs ps restart migrate

up:
	$(DC) up -d --build

down:
	$(DC) down

build:
	$(DC) build

logs:
	$(DC) logs -f

ps:
	$(DC) ps

restart:
	$(DC) restart api bot

migrate:
	$(DC) exec api alembic upgrade head
