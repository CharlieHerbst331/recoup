PYTHON := .venv/bin/python

.PHONY: check
check:
	$(PYTHON) -m ruff check recoup tests
	$(PYTHON) -m ruff format --check recoup tests
	RECOUP_LLM=fake $(PYTHON) -m pytest
