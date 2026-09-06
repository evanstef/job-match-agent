#!/bin/sh
set -e

# migrasi DB dulu, baru serahkan ke CMD (uvicorn)
alembic upgrade head
exec "$@"
