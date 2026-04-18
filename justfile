set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

default:
    @just --list

setup:
    uv sync

run:
    uv run python -m src.main

shell:
    PYTHONPATH=src uv run python -i -c "from config import settings; from database import models; from database.config import async_session_maker, engine"

makemigrations message="auto_migration" autogenerate="true":
    if [[ "{{autogenerate}}" == "true" ]]; then \
      uv run alembic -c src/database/alembic.ini revision --autogenerate -m "{{message}}"; \
    else \
      uv run alembic -c src/database/alembic.ini revision -m "{{message}}"; \
    fi

migrate revision="head":
    uv run alembic -c src/database/alembic.ini upgrade "{{revision}}"

downgrade revision="-1":
    uv run alembic -c src/database/alembic.ini downgrade "{{revision}}"

lint:
    uv run ruff check .

format:
    uv run black .

ty:
    uv run ty check src --extra-search-path src --exclude migrations --exclude src/tests --exclude tests --exclude test

test:
    uv run pytest src/tests

check:
    uv run ruff check . --fix
    uv run black .
    uv run ty check src --extra-search-path src --exclude migrations --exclude src/tests --exclude tests --exclude test
    uv run pytest src/tests

build:
    uv build
