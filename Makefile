.PHONY: setup run test lint catalog clean

setup:
	python3 -m venv .venv
	.venv/bin/pip install -e ".[dev]"

run:
	.venv/bin/python -m dat_gov.cli all

test:
	.venv/bin/python -m pytest -q

lint:
	.venv/bin/ruff check src tests scripts

catalog:
	.venv/bin/python -m dat_gov.cli catalog

clean:
	rm -rf data/raw data/bronze data/silver data/gold data/quarantine data/*.duckdb data/quality_report.json data/lineage.json docs/catalog.md docs/lineage.md
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache
