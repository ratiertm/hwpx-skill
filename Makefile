PYTEST ?= pytest

.PHONY: test-smoke test-integration test-regression test-ci test-full

test-smoke:
	$(PYTEST) -m "smoke"

test-integration:
	$(PYTEST) -m "integration"

test-regression:
	$(PYTEST) -m "regression"

test-ci:
	$(PYTEST) -m "smoke or integration"

test-full:
	$(PYTEST)
