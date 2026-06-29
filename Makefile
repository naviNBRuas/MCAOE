.PHONY: setup lint format typecheck test check all

setup:
	pip install hatch pre-commit
	pre-commit install

lint:
	hatch run ruff check .

format:
	hatch run ruff format .

typecheck:
	hatch run mypy src tests

test:
	hatch run pytest

check: lint typecheck test

all: format check
