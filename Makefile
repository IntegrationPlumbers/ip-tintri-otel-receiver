.PHONY: help install install-dev test test-coverage lint format type-check clean run validate

help:
	@echo "Tintri OpenTelemetry Receiver - Development Commands"
	@echo ""
	@echo "  install          Install package"
	@echo "  install-dev      Install package with development dependencies"
	@echo "  test             Run unit tests"
	@echo "  test-coverage    Run tests with coverage report"
	@echo "  lint             Run linting checks"
	@echo "  format           Format code with black"
	@echo "  type-check       Run type checking with mypy"
	@echo "  clean            Clean build artifacts"
	@echo "  run              Run receiver with example config"
	@echo "  validate         Validate example configuration"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

test-coverage:
	pytest tests/ --cov=tintri_receiver --cov-report=html --cov-report=term-missing

lint:
	flake8 src/tintri_receiver tests/ --max-line-length=100 --ignore=E203,W503

format:
	black src/tintri_receiver tests/ --line-length=88

type-check:
	mypy src/tintri_receiver --ignore-missing-imports

clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:
	@echo "Note: Update config.example.yaml with your credentials first"
	tintri-receiver --config config.example.yaml

validate:
	tintri-receiver --config config.example.yaml --validate
