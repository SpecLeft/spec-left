SHELL := /bin/sh

.PHONY: test pre-commit lint lint-fix

test:
	pytest tests/

pre-commit:
	pre-commit run --all-files

lint:
	ruff check src/ tests/ examples/
	mypy src/
	black --check src/ tests/ examples/

lint-fix:
	ruff check --fix src/ tests/ examples/
	black src/ tests/ examples/
