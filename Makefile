# Makefile for DexScraper package

.PHONY: help install install-dev test lint format build publish clean run stream export

# Default Python command (use pyenv if available)
PYTHON := $(shell which pyenv > /dev/null 2>&1 && echo 'eval "$$(pyenv init -)" && python' || echo 'python3')
PIP := $(shell which pyenv > /dev/null 2>&1 && echo 'eval "$$(pyenv init -)" && pip' || echo 'pip3')

help: ## Show this help message
	@echo "DexScraper Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install package dependencies
	$(PYTHON) -m pip install -e .

install-dev: ## Install package with development dependencies
	$(PYTHON) -m pip install -e ".[dev]"
	$(PYTHON) -m pip install pytest pytest-asyncio pytest-cov black isort flake8 mypy rich pre-commit bandit safety

test: ## Run all tests
	$(PYTHON) -m pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage
	$(PYTHON) -m pytest tests/ --cov=dexscraper --cov-report=html --cov-report=term

test-models: ## Run only model tests
	$(PYTHON) -m pytest tests/test_models.py -v

test-config: ## Run only config tests
	$(PYTHON) -m pytest tests/test_config.py -v

test-integration: ## Run integration tests (requires network)
	$(PYTHON) -m pytest tests/test_enhanced_ohlc.py::test_enhanced_ohlc_output -v -s

lint: ## Run code linting
	$(PYTHON) -m flake8 dexscraper/ tests/ --max-line-length=120 --ignore=E203,W503

format: ## Format code with black
	$(PYTHON) -m black dexscraper/ tests/ --line-length=120

type-check: ## Run type checking with mypy
	$(PYTHON) -m mypy dexscraper/ --ignore-missing-imports

# Pre-commit and code quality
precommit-install: ## Install pre-commit hooks
	pre-commit install

precommit: ## Run all pre-commit hooks
	pre-commit run --all-files

precommit-update: ## Update pre-commit hooks
	pre-commit autoupdate

format-imports: ## Sort imports with isort
	$(PYTHON) -m isort dexscraper/ tests/ --profile black

format-all: format format-imports ## Format code and sort imports

security: ## Run security checks
	$(PYTHON) -m bandit -r dexscraper/ -f json -o bandit-report.json || true
	$(PYTHON) -m safety check --json --output safety-report.json || true

check: lint type-check ## Run all code quality checks

check-all: format-all lint type-check security ## Run all checks including security

build: ## Build distribution packages
	$(PYTHON) -m pip install build
	$(PYTHON) -m build

publish-test: build ## Publish to TestPyPI
	$(PYTHON) -m pip install twine
	$(PYTHON) -m twine upload --repository testpypi dist/*

publish: build ## Publish to PyPI (production)
	$(PYTHON) -m pip install twine
	$(PYTHON) -m twine upload dist/*

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# CLI Usage Commands
run: ## Run basic scraper (JSON output)
	$(PYTHON) -m dexscraper

stream: ## Run streaming scraper with Rich output
	$(PYTHON) -c "import asyncio; from dexscraper.cli import main; asyncio.run(main())"

stream-pumpfun: ## Stream Pumpfun trending tokens
	$(PYTHON) -c "import asyncio; from dexscraper import DexScraper; from dexscraper.config import PresetConfigs; scraper = DexScraper(debug=False); config = PresetConfigs.pumpfun_trending(); scraper.config = config; asyncio.run(scraper.stream_pairs(output_format='json'))"

export-csv: ## Export current data to CSV
	$(PYTHON) -c "import asyncio; from dexscraper import DexScraper; async def export(): scraper = DexScraper(); batch = await scraper.extract_token_data(); print(f'Exported: {batch.export_csv(\"tokens.csv\", \"ohlcvt\")}'); asyncio.run(export())"

export-mt5: ## Export current data to MT5 format
	$(PYTHON) -c "import asyncio; from dexscraper import DexScraper; async def export(): scraper = DexScraper(); batch = await scraper.extract_token_data(); print(f'Exported: {batch.export_mt5(\"tokens.mt5\")}'); asyncio.run(export())"

demo: ## Run demo extraction and display results
	$(PYTHON) -c "import asyncio; from dexscraper import DexScraper; async def demo(): scraper = DexScraper(); batch = await scraper.extract_token_data(); print(f'📊 Extracted {batch.total_extracted} tokens, {batch.high_confidence_count} high-confidence'); [print(f'  {t.get_display_name()}: $${t.price:.8f} | Vol: $${t.volume_24h:,.0f}') for t in batch.get_top_tokens(5) if t.price]; asyncio.run(demo())"

# Development shortcuts
dev-setup: install-dev precommit-install ## Complete development setup
	@echo "✅ Development environment ready!"
	@echo "🧪 Run 'make test' to run tests"
	@echo "🚀 Run 'make demo' to test extraction"
	@echo "🔧 Run 'make precommit' to run all quality checks"

quick-test: test-models test-config ## Quick test suite (no network required)

full-test: test test-integration ## Full test suite including integration tests

# Version and release helpers
version: ## Show current version
	$(PYTHON) -c "from dexscraper import __version__; print(__version__)"

release-check: clean test lint type-check build ## Full release validation
	@echo "✅ Release validation complete!"
	@echo "📦 Built packages in dist/"
	@echo "🚀 Ready to publish with 'make publish'"

# Documentation
docs: ## Generate documentation
	@echo "📚 Documentation generation not yet implemented"

# Docker support
docker-build: ## Build Docker image
	docker build -t dexscraper .

docker-run: ## Run in Docker container
	docker run --rm -it dexscraper

# Examples and usage
examples: ## Show usage examples
	@echo "DexScraper Usage Examples:"
	@echo ""
	@echo "📊 Basic extraction:"
	@echo "  make demo"
	@echo ""
	@echo "🔄 Streaming data:"
	@echo "  make stream"
	@echo ""
	@echo "💾 Export to CSV:"
	@echo "  make export-csv"
	@echo ""
	@echo "📈 Export to MT5:"
	@echo "  make export-mt5"
	@echo ""
	@echo "🧪 Run tests:"
	@echo "  make test"
