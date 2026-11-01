PYTHON ?= python3

# Harness tests, then the reference/exploit matrix. No model calls.
test:
	$(PYTHON) -m pytest tests -q
	$(PYTHON) -m gg invariants

.PHONY: test
