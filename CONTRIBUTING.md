# Contributing to DexScraper

We welcome contributions! This guide will help you get started with developing and contributing to DexScraper.

## 🚀 Development Setup

### Prerequisites

- Python 3.7+
- Git

### Quick Start

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/dexscraper.git
   cd dexscraper
   ```

2. **Install Development Dependencies**
   ```bash
   pip install -e .[dev]
   ```

3. **Install Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

4. **Verify Installation**
   ```bash
   pytest tests/ -v
   ```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dexscraper --cov-report=html

# Run specific test categories
pytest -m integration  # Integration tests
pytest -m "not slow"   # Skip slow tests

# Run specific test file
pytest tests/test_scraper.py -v
```

### Test Structure

- **Unit Tests**: Individual functions and classes
  - `tests/test_scraper.py`: Core scraper functionality
  - `tests/test_config.py`: Configuration validation
  - `tests/test_models.py`: Data model serialization
  - `tests/test_cli.py`: CLI interface testing

- **Integration Tests**: End-to-end scenarios
  - `tests/test_enhanced_ohlc.py`: OHLC data processing
  - `tests/test_edge_cases.py`: Protocol edge cases

- **Protocol Tests**: Binary data handling
  - `tests/test_decode_pair.py`: Pair decoding edge cases

## 🔧 Code Quality

### Formatting and Linting

```bash
# Format code
black dexscraper/ tests/

# Sort imports
isort dexscraper/ tests/

# Lint code
flake8 dexscraper/

# Type check
mypy dexscraper/

# Run all pre-commit hooks
pre-commit run --all-files
```

### Code Style Guidelines

- **Black**: Code formatting (88 char line length)
- **isort**: Import sorting with black profile
- **flake8**: Linting with E203 extension ignored
- **mypy**: Type checking with strict settings
- **pytest**: Testing framework

### Pre-commit Hooks

We use pre-commit hooks to ensure code quality:

- Trailing whitespace removal
- End of file fixing
- YAML validation
- Large file checks
- Merge conflict detection
- Debug statement detection
- Black formatting
- isort import sorting
- flake8 linting
- mypy type checking
- bandit security scanning

## 🏗️ Architecture

### Package Structure

```
dexscraper/
├── __init__.py          # Package exports and version
├── scraper.py           # Main DexScraper class
├── config.py            # Configuration classes and enums
├── models.py            # Data models (TradingPair, TokenProfile, etc.)
├── protocol.py          # Binary protocol decoder (legacy)
├── enhanced_protocol.py # Enhanced protocol with OHLC support
├── cloudflare_bypass.py # Cloudflare bypass utilities
├── cli.py               # Rich-based CLI interface
├── logger.py            # Logging configuration
├── utils.py             # Utility functions
└── _version.py          # Auto-generated version (setuptools-scm)
```

### Key Components

- **DexScraper**: Main class for WebSocket connections and data extraction
- **ScrapingConfig**: Configuration system with presets
- **Models**: Data structures for trading pairs, OHLC data, and token profiles
- **CLI**: Rich-based command-line interface
- **Protocol Decoders**: Binary protocol handlers for DexScreener's data format

## 🐛 Reporting Issues

### Bug Reports

Please include:

1. **Environment**: Python version, OS, package versions
2. **Steps to reproduce**: Clear, minimal reproduction case
3. **Expected behavior**: What should happen
4. **Actual behavior**: What actually happens
5. **Logs**: Any error messages or debug output

### Feature Requests

Please include:

1. **Use case**: Why is this feature needed?
2. **Proposed solution**: How should it work?
3. **Alternatives**: Other solutions you've considered

## 🎯 Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write code following our style guidelines
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run tests
pytest

# Check code quality
pre-commit run --all-files

# Manual testing
python -m dexscraper --help
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: add your feature description"
```

We use conventional commit messages:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Adding or updating tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

### 5. Submit Pull Request

1. Push your branch to your fork
2. Create a pull request against the main branch
3. Fill out the pull request template
4. Wait for review and address feedback

## 🔒 Security

### Security Scanning

We use several security tools:

```bash
# Dependency vulnerability scanning
safety check

# Code security analysis
bandit -r dexscraper/

# Check for secrets in code
pre-commit run --all-files
```

### Reporting Security Issues

For security vulnerabilities, please email directly instead of creating a public issue.

## 📦 Release Process

### Version Management

- We use `setuptools-scm` for automatic version management
- Versions are derived from git tags
- Development versions include commit information

### Creating Releases

1. **Prepare Release**
   ```bash
   # Ensure main branch is clean
   git checkout main
   git pull origin main

   # Run full test suite
   pytest tests/ -v

   # Check package build
   python -m build
   python -m twine check dist/*
   ```

2. **Tag Release**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

3. **GitHub Release**
   - Create release on GitHub
   - This triggers automatic PyPI deployment via GitHub Actions

## 🎨 UI/UX Guidelines

### CLI Design

- Use Rich library for enhanced terminal output
- Provide both simple and interactive modes
- Include helpful error messages and suggestions
- Support multiple output formats (JSON, CSV, OHLC, etc.)

### Color Schemes

- **Magenta/Purple**: Primary brand colors
- **Green**: Success, positive values
- **Red**: Errors, negative values
- **Blue**: Information, neutral values
- **Yellow**: Warnings, caution

## 📚 Documentation

### Code Documentation

- Use docstrings for all public functions and classes
- Include type hints for all function signatures
- Document complex algorithms and protocol details
- Provide usage examples in docstrings

### User Documentation

- Update README.md for user-facing changes
- Update CLAUDE.md for development guidance
- Include examples for new features
- Document configuration options

## 🤝 Community Guidelines

### Code of Conduct

- Be respectful and professional
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Respect different perspectives and experience levels

### Communication

- Use GitHub Issues for bug reports and feature requests
- Use GitHub Discussions for questions and general discussion
- Be clear and concise in communication
- Include relevant context and examples

## 🙏 Recognition

Contributors will be recognized in:

- GitHub contributors list
- Release notes for significant contributions
- Documentation credits

Thank you for contributing to DexScraper! 🚀
