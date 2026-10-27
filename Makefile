# Simple local development shortcuts.

VENV ?= .venv
VENV_PY := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
VENV_PRECOMMIT := $(VENV)/bin/pre-commit

ifeq ($(wildcard $(VENV_PY)),)
PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
PRECOMMIT ?= pre-commit
else
PYTHON ?= $(VENV_PY)
PIP ?= $(VENV_PIP)
PRECOMMIT ?= $(VENV_PRECOMMIT)
endif

define warn_if_no_venv
@if [ ! -f "$(VENV_PY)" ]; then \
  echo "[warn] Virtual environment $(VENV) not found; using system tools."; \
fi
endef

.DEFAULT_GOAL := help

.PHONY: help setup-venv install install-dev test test-live lint format mypy check precommit-install precommit build clean

help:
	@echo "Available targets:"
	@echo "  setup-venv       Create virtual environment in $(VENV)"
	@echo "  install          Install package"
	@echo "  install-dev      Install package with dev dependencies"
	@echo "  test             Run test suite (offline; skips live network)"
	@echo "  test-live        Run live WebSocket tests (DEXSCRAPER_LIVE=1)"
	@echo "  lint             Run Ruff lint checks"
	@echo "  format           Apply Ruff formatting/fixes"
	@echo "  mypy             Run static type checking"
	@echo "  check            Run lint + mypy + tests"
	@echo "  precommit-install Install git pre-commit hooks"
	@echo "  precommit        Run all pre-commit hooks"
	@echo "  build            Build source/wheel distributions"
	@echo "  clean            Remove local caches and build artifacts"

setup-venv:
	python3 -m venv $(VENV)

install:
	$(call warn_if_no_venv)
	$(PIP) install -e .

install-dev:
	$(call warn_if_no_venv)
	$(PIP) install -e ".[dev]"

test:
	$(call warn_if_no_venv)
	$(PYTHON) -m pytest -q -m "not integration and not live"

test-live:
	$(call warn_if_no_venv)
	DEXSCRAPER_LIVE=1 $(PYTHON) -m pytest -q -m "integration or live"

lint:
	$(call warn_if_no_venv)
	$(PYTHON) -m ruff check dexscraper tests

format:
	$(call warn_if_no_venv)
	$(PYTHON) -m ruff check --fix dexscraper tests
	$(PYTHON) -m ruff format dexscraper tests

format-check:
	$(call warn_if_no_venv)
	$(PYTHON) -m ruff format --check dexscraper tests

mypy:
	$(call warn_if_no_venv)
	$(PYTHON) -m mypy dexscraper

check: lint format-check mypy test

precommit-install:
	$(call warn_if_no_venv)
	$(PRECOMMIT) install

precommit:
	$(call warn_if_no_venv)
	$(PRECOMMIT) run --all-files

build:
	$(call warn_if_no_venv)
	$(PYTHON) -m build

clean:
	@rm -rf build dist htmlcov .pytest_cache .mypy_cache .ruff_cache
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
