# Harness tests, then the reference/exploit matrix. No model calls.
# Without PYTHON, the first run builds .venv from requirements.txt; pass
# PYTHON=<interpreter> to use one that already has the pinned pytest.
BOOTSTRAP ?= python3
PYTHON ?= .venv/bin/python

test: $(if $(filter .venv/bin/python,$(PYTHON)),.venv/.installed)
	@$(PYTHON) -c "import pytest" 2>/dev/null || { \
		echo "pytest is not installed for $(PYTHON). Run: $(PYTHON) -m pip install -r requirements.txt" >&2; exit 1; }
	$(PYTHON) -m pytest tests -q
	$(PYTHON) -m gg invariants

.venv/.installed: requirements.txt
	@$(BOOTSTRAP) -c "import sys; sys.exit(sys.version_info < (3, 11))" || { \
		echo "$(BOOTSTRAP) is older than 3.11. Run: make test BOOTSTRAP=<python3.11 or newer>" >&2; exit 1; }
	$(BOOTSTRAP) -m venv .venv
	.venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt
	touch $@

.PHONY: test
