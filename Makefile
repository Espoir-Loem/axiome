PY ?= .venv/bin/python

.PHONY: help venv lint format typecheck test cov determinism check run clean

help:  ## Affiche cette aide
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*## "}{printf "  %-12s %s\n", $$1, $$2}'

venv:  ## Crée l'environnement de développement
	uv venv .venv && uv pip install --python $(PY) -e '.[dev]'

lint:  ## Analyse statique (ruff)
	$(PY) -m ruff check src tests
	$(PY) -m ruff format --check src tests

format:  ## Formate le code
	$(PY) -m ruff format src tests
	$(PY) -m ruff check --fix src tests

typecheck:  ## Typage strict (mypy --strict)
	$(PY) -m mypy

test:  ## Tests unitaires, intégration, propriétés
	$(PY) -m pytest

cov:  ## Tests + couverture (seuil 90 %)
	$(PY) -m pytest --cov --cov-report=term-missing

determinism:  ## Même entrée → même sortie, octet pour octet
	$(PY) -m pytest tests/determinism

check: lint typecheck cov  ## Porte de qualité complète (= CI)

run:  ## Lance le REPL
	$(PY) -m axiome

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage build dist src/*.egg-info
