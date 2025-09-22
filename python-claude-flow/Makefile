# Makefile for Claude-Flow Python testing and development

.PHONY: help install-deps install-test-deps test test-unit test-integration test-e2e test-performance test-quick test-coverage clean-test

# Default target
help:
	@echo "Claude-Flow Python Testing Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install-deps       Install production dependencies"
	@echo "  install-test-deps  Install testing dependencies"
	@echo "  test              Run all tests with coverage"
	@echo "  test-unit         Run unit tests only"
	@echo "  test-integration  Run integration tests only"
	@echo "  test-e2e          Run end-to-end tests only"
	@echo "  test-performance  Run performance tests only"
	@echo "  test-quick        Run quick test suite (unit tests, no coverage)"
	@echo "  test-coverage     Generate coverage report"
	@echo "  quality-check     Run code quality checks"
	@echo "  clean-test        Clean test artifacts"
	@echo "  setup-test-env    Setup complete test environment"

# Dependency installation
install-deps:
	python -m pip install -r requirements.txt

install-test-deps:
	python -m pip install -r requirements-test.txt

# Test execution
test:
	python tests/python/run_tests.py all --verbose

test-unit:
	python tests/python/run_tests.py unit --verbose

test-integration:
	python tests/python/run_tests.py integration --verbose

test-e2e:
	python tests/python/run_tests.py e2e --verbose

test-performance:
	python tests/python/run_tests.py performance --verbose

test-quick:
	python tests/python/run_tests.py quick

# Coverage reporting
test-coverage:
	python -m pytest tests/python/unit/ --cov=src/claude_flow --cov-report=html --cov-report=term-missing --cov-report=xml

# Code quality
quality-check:
	python tests/python/run_tests.py all --quality-check

lint:
	python -m flake8 src/claude_flow --max-line-length=100 --ignore=E203,W503

format:
	python -m black src/claude_flow tests/python/
	python -m isort src/claude_flow tests/python/

format-check:
	python -m black --check src/claude_flow tests/python/
	python -m isort --check-only src/claude_flow tests/python/

# Cleanup
clean-test:
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf tests/python/__pycache__/
	rm -rf tests/python/*/__pycache__/
	rm -rf tests/python/*/*/__pycache__/
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +

clean-all: clean-test
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/

# Environment setup
setup-test-env: install-deps install-test-deps
	@echo "Test environment setup complete"

# CI/CD targets
ci-test: setup-test-env
	python tests/python/run_tests.py all --report=test-results.json

ci-quick: install-test-deps
	python tests/python/run_tests.py quick

# Development targets
dev-test:
	python tests/python/run_tests.py unit --verbose

watch-tests:
	python -m pytest tests/python/unit/ --verbose -f

# Specific test execution
test-config:
	python -m pytest tests/python/unit/test_config.py -v

test-events:
	python -m pytest tests/python/unit/test_events.py -v

test-claude:
	python -m pytest tests/python/unit/test_claude.py -v

test-agents:
	python -m pytest tests/python/integration/test_agents.py -v

test-workflows:
	python -m pytest tests/python/e2e/test_workflows.py -v

test-performance-load:
	python -m pytest tests/python/performance/test_load_testing.py -v

# Documentation
test-docs:
	@echo "Running documentation tests (if implemented)"

# Release preparation
pre-release: clean-all setup-test-env quality-check test
	@echo "Pre-release checks complete"