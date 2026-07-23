# SynthAudit-Bench developer Makefile.
# Pipeline targets (fetch, audit, aggregate, stats, figures, release, reproduce)
# are wired to the `bench` CLI as each is implemented in its work package; only
# targets whose implementation exists are defined here (no broken recipes).

.PHONY: help setup lint format type imports test check docs clean

help:
	@echo "setup   - install the package with dev extras"
	@echo "lint    - ruff lint"
	@echo "format  - ruff format (in place)"
	@echo "type    - mypy (strict)"
	@echo "imports - import-linter contracts"
	@echo "test    - pytest with coverage"
	@echo "check   - lint + format check + type + imports + test (the CI gate)"
	@echo "docs    - build the documentation site"
	@echo "clean   - remove caches and generated outputs"

setup:
	python -m pip install -e ".[dev]"

lint:
	ruff check .

format:
	ruff format .

type:
	python -m mypy

imports:
	lint-imports

test:
	python -m pytest

check:
	ruff check .
	ruff format --check .
	python -m mypy
	lint-imports
	python -m pytest

docs:
	python -m mkdocs build

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml
	rm -rf results figures build dist
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
