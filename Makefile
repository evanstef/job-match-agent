.DEFAULT_GOAL := help
.PHONY: help setup install-api install-web api web db db-down db-logs test lint fmt \
	migrasi upgrade downgrade migrasi-history migrasi-current

API_DIR := apps/api
WEB_DIR := apps/web

# satu-satunya berkas konfigurasi dipakai bareng aplikasi & compose,
# supaya tidak ada .env kedua yang diam-diam berisi nilai lain
COMPOSE := docker compose --env-file $(API_DIR)/.env

help: ## Tampilkan daftar perintah
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: install-api install-web ## Pasang semua dependency (api + web)
	@test -f $(API_DIR)/.env || (cp $(API_DIR)/.env.example $(API_DIR)/.env && echo "-> $(API_DIR)/.env dibuat dari contoh, isi dulu nilainya")

install-api: ## Pasang dependency Python
	cd $(API_DIR) && uv sync

install-web: ## Pasang dependency Node
	cd $(WEB_DIR) && pnpm install

api: ## Jalankan API (http://localhost:8010)
	cd $(API_DIR) && uv run uvicorn job_match_api.main:app --reload --port 8010 --app-dir src

web: ## Jalankan web (http://localhost:3010)
	cd $(WEB_DIR) && pnpm dev --port 3010

db: ## Nyalakan Postgres + pgvector (port 5433)
	$(COMPOSE) up -d db

db-down: ## Matikan Postgres (data tetap aman di volume)
	$(COMPOSE) down

db-logs: ## Lihat log Postgres
	$(COMPOSE) logs -f db

test: ## Jalankan test Python
	cd $(API_DIR) && uv run pytest

lint: ## Cek gaya kode Python
	cd $(API_DIR) && uv run ruff check src tests

fmt: ## Rapikan kode Python (format + urutan import)
	cd $(API_DIR) && uv run ruff check --fix src tests && uv run ruff format src tests

migrasi: ## Bikin file migrasi baru dari perubahan models.py — pakai: make migrasi m="pesannya"
	cd $(API_DIR) && uv run alembic revision --autogenerate -m "$(m)"

upgrade: ## Jalankan migrasi yang belum dieksekusi ke database
	cd $(API_DIR) && uv run alembic upgrade head

downgrade: ## Mundur satu migrasi
	cd $(API_DIR) && uv run alembic downgrade -1

migrasi-history: ## Lihat semua migrasi yang pernah dibuat
	cd $(API_DIR) && uv run alembic history

migrasi-current: ## Lihat migrasi mana yang aktif di database sekarang
	cd $(API_DIR) && uv run alembic current
