.DEFAULT_GOAL := help
.PHONY: help setup install-api install-web api web db db-down db-logs test lint fmt

API_DIR := apps/api
WEB_DIR := apps/web

help: ## Tampilkan daftar perintah
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: install-api install-web ## Pasang semua dependency (api + web)
	@test -f .env || (cp .env.example .env && echo "-> .env dibuat dari contoh, isi dulu nilainya")

install-api: ## Pasang dependency Python
	cd $(API_DIR) && uv sync

install-web: ## Pasang dependency Node
	cd $(WEB_DIR) && pnpm install

api: ## Jalankan API (http://localhost:8010)
	cd $(API_DIR) && uv run uvicorn job_match_api.main:app --reload --port 8010 --app-dir src

web: ## Jalankan web (http://localhost:3010)
	cd $(WEB_DIR) && pnpm dev --port 3010

db: ## Nyalakan Postgres + pgvector (port 5433)
	docker compose up -d db

db-down: ## Matikan Postgres (data tetap aman di volume)
	docker compose down

db-logs: ## Lihat log Postgres
	docker compose logs -f db

test: ## Jalankan test Python
	cd $(API_DIR) && uv run pytest

lint: ## Cek gaya kode Python
	cd $(API_DIR) && uv run ruff check src tests

fmt: ## Rapikan kode Python
	cd $(API_DIR) && uv run ruff format src tests
