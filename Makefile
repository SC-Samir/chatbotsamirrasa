SHELL := /bin/bash

.PHONY: help sync sync-dev train build up down restart ps logs app-logs worker-logs redis-logs test clean

help:
	@echo "Targets disponibles:"
	@echo "  make sync        -> Installe les deps app via uv"
	@echo "  make sync-dev    -> Installe les deps app + dev via uv"
	@echo "  make train       -> Entraine le modele Rasa (docker compose profile train)"
	@echo "  make build       -> Build les images Docker"
	@echo "  make up          -> Lance app + worker + redis"
	@echo "  make down        -> Arrete tous les services"
	@echo "  make restart     -> Redemarre app + worker + redis"
	@echo "  make ps          -> Liste les services"
	@echo "  make logs        -> Logs de tous les services"
	@echo "  make app-logs    -> Logs du service app"
	@echo "  make worker-logs -> Logs du worker"
	@echo "  make redis-logs  -> Logs de Redis"
	@echo "  make test        -> Lance la suite de tests"
	@echo "  make clean       -> Stop + supprime volumes orphelins"

sync:
	python3 -m uv sync --frozen

sync-dev:
	python3 -m uv sync --frozen --group dev

train:
	docker compose --profile train run --rm --build rasa-train

build:
	docker compose build

up:
	docker compose up -d app worker redis

down:
	docker compose down

restart: down up

ps:
	docker compose ps

logs:
	docker compose logs -f

app-logs:
	docker compose logs -f app

worker-logs:
	docker compose logs -f worker

redis-logs:
	docker compose logs -f redis

test:
	python3 -m pytest -q

clean:
	docker compose down -v --remove-orphans
