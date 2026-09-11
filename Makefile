.PHONY: test

test:
	@if [ -x .venv/bin/python ]; then \
		.venv/bin/python -m pytest; \
	else \
		python -m pytest; \
	fi
