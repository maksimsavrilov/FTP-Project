.PHONY: test

test:
	@if [ -x .venv/bin/python ]; then \
		.venv/bin/python -m pytest; \
	else \
		python -m pytest; \
	fi


lint:
	ruff check agent

format-check:
	ruff format --check agent

type-check:
	mypy agent


quality: lint format-check type-check test