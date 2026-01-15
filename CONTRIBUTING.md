# Contributing to SpecLeft SDK

Thank you for your interest in contributing to SpecLeft SDK! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- pip (Python package installer)
- Git

### Setting Up the Development Environment

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/spec-left.git
   cd spec-left
   ```

2. **Create a virtual environment (recommended):**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install pinned dependencies and the package in development mode:**

   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   pip install -e .
   ```

4. **Verify the installation:**

   ```bash
   specleft --version
   pytest --version
   ```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Tests with Coverage

```bash
pytest --cov=src/specleft tests/
```

### Run Tests with Coverage Report

```bash
pytest --cov=src/specleft --cov-report=html tests/
# Open htmlcov/index.html in your browser
```

### Run Specific Test Files

```bash
pytest tests/test_schema.py
pytest tests/test_decorators.py
pytest tests/test_pytest_plugin.py
pytest tests/test_cli.py
```

### Run Tests Matching a Pattern

```bash
pytest -k "test_specleft"
```

### Run Tests with Verbose Output

```bash
pytest -v
```

## Code Style Guidelines

### Formatting

We use **Black** for code formatting with default settings:

```bash
# Format all code
black src/ tests/

# Check formatting without making changes
black --check src/ tests/
```

### Linting

We use **Ruff** for linting:

```bash
# Run linter
ruff check src/ tests/

# Auto-fix issues where possible
ruff check --fix src/ tests/
```

### Type Checking

We use **MyPy** for static type checking:

```bash
mypy src/
```

### Code Style Summary

- Use type hints for all function parameters and return values
- Write docstrings for all public functions, classes, and modules
- Follow PEP 8 naming conventions:
  - `snake_case` for functions and variables
  - `PascalCase` for classes
  - `UPPER_SNAKE_CASE` for constants
- Keep functions focused and small (ideally under 50 lines)
- Use `pathlib.Path` for file operations instead of `os.path`

## Project Structure

```
spec-left/
├── src/specleft/           # Main package source
│   ├── __init__.py         # Public API exports
│   ├── decorators.py       # @specleft and @reusable_step decorators
│   ├── schema.py           # Pydantic models for features.json
│   ├── pytest_plugin.py    # Pytest hooks integration
│   ├── collector.py        # Result collection and JSON output
│   ├── cli/                # CLI commands
│   │   ├── __init__.py
│   │   └── main.py
│   └── templates/          # Jinja2 templates
│       ├── skeleton_test.py.jinja2
│       └── report.html.jinja2
├── tests/                  # Test suite
│   ├── test_schema.py
│   ├── test_decorators.py
│   ├── test_pytest_plugin.py
│   └── test_cli.py
├── examples/               # Example usage
│   ├── features.json
│   └── test_example.py
├── pyproject.toml          # Project configuration
├── README.md               # User documentation
└── CONTRIBUTING.md         # This file
```

## Making Changes

### Before You Start

1. Check existing issues to see if your change is already being worked on
2. For major changes, open an issue first to discuss the approach
3. Fork the repository and create a feature branch

### Development Workflow

1. **Create a feature branch:**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Write tests for new functionality
   - Update documentation if needed
   - Follow the code style guidelines

3. **Run the test suite:**

   ```bash
   pytest
   ```

4. **Run code quality checks:**

   ```bash
   black src/ tests/
   ruff check src/ tests/
   mypy src/
   ```

5. **Commit your changes:**

   ```bash
   git add .
   git commit -m "Add feature: brief description"
   ```

6. **Push and create a pull request:**

   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Guidelines

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Keep the first line under 72 characters
- Reference issues and pull requests where appropriate

Examples:
- `Add reusable step decorator with parameter interpolation`
- `Fix auto-skip not working when features.json is missing`
- `Update README with CLI command examples`

## Testing Guidelines

### Writing Tests

- Place tests in the `tests/` directory
- Name test files with the `test_` prefix
- Name test functions with the `test_` prefix
- Use descriptive test names that explain what is being tested
- Follow the Arrange-Act-Assert (AAA) pattern

### Test Example

```python
def test_specleft_decorator_stores_metadata():
    """Test that @specleft decorator stores feature_id and scenario_id."""
    # Arrange
    @specleft(feature_id="TEST-001", scenario_id="test-scenario")
    def dummy_test():
        pass

    # Act & Assert
    assert hasattr(dummy_test, '_specleft_feature_id')
    assert dummy_test._specleft_feature_id == "TEST-001"
    assert dummy_test._specleft_scenario_id == "test-scenario"
```

### Test Coverage

- Aim for at least 80% code coverage
- All public APIs should have tests
- Include tests for edge cases and error conditions

## Documentation

- Update the README.md for user-facing changes
- Add docstrings to all public functions and classes
- Include examples in docstrings where helpful
- Update PROGRESS.md when completing implementation phases

## Questions?

If you have questions about contributing, feel free to:
- Open an issue for discussion
- Check existing issues and pull requests for context

Thank you for contributing to SpecLeft SDK!
