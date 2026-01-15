# SpecLeft SDK

A test management SDK for pytest that enables structured test metadata, step-by-step result tracking, and automated test generation from JSON specifications.

## What is SpecLeft?

SpecLeft turns your pytest tests into traceable, reportable assets that actually connect to your feature specifications.

Ever felt like your tests and specs live in completely different universes? SpecLeft is here to fix that disconnect.

SpecLeft wraps around pytest to inject structure, visibility, and traceability into your testing without requiring a PhD in test framework configuration or vendor lock-in nightmares.

The philosophy is straightforward: **steal the best ideas from Behaviour Driven Development (BDD)**, **keep the pragmatism of Test Driven Development (TDD)**, and **drop all the ceremonial overhead**. The result? A framework that actually lets developers, QAs, and product teams speak the same language about what the software should do—without the ceremony, the bloat, or the spreadsheets.

SpecLeft enables truly **Shift Left** testing by making it trivially easy to go from "what should we build?" to "here's the test skeleton" to "here's what actually happened"—all in code, all under version control, all without leaving your IDE.

## Features

- 🏷️ **Spec-Defined Tests**: Decorate your pytest functions with feature IDs, scenario IDs, priorities, and tags. Your tests become discoverable, traceable, and first-class citizens in your codebase.

- 🔍 **Step-by-Step Tracing**: Record individual test steps with timing, pass/fail status, and parameter interpolation. Watch exactly where your tests succeed—or crash—with surgical precision.

- 🏗️ **Skeleton Test Generation**: Write a simple JSON file describing your features and scenarios. SpecLeft generates fully-formed test skeletons with proper decorators, parameterization, and step placeholders. Stop writing boilerplate; start writing behavior.

- 📊 **Self-Hosted Test Reports**: Generate beautiful, interactive HTML reports from test execution results. No third-party vendor, no subscriptions, no data leaving your infrastructure.

- 🎯 **Dynamic Pytest Markers**: Scenario tags are automatically injected as pytest markers, so you can slice and dice test execution with `pytest -m "smoke"` or `pytest -m "critical"`. Filter tests like a pro.

- ⚡ **Zero-Config Pytest Integration**: Installs as a pytest plugin. No complex setup, no configuration files to debug. Just `pip install specleft`, run your tests, and watch the magic happen.

## What's Next?

SpecLeft is actively evolving. Check out [ROADMAP.md](./ROADMAP.md) for what we're building next.

## Installation

```bash
pip install -e spec-left

# With development dependencies
pip install -e "spec-left[dev]"
```

## Quick Start

### 1. Define Features (features.json)

Create a `features.json` file describing your test scenarios:

```json
{
  "version": "1.0",
  "features": [
    {
      "id": "AUTH-001",
      "name": "User Authentication",
      "description": "Users can securely log in and out of the system",
      "metadata": {
        "owner": "auth-team",
        "component": "authentication",
        "priority": "critical"
      },
      "scenarios": [
        {
          "id": "login-success",
          "name": "Successful login with valid credentials",
          "priority": "critical",
          "tags": ["smoke", "authentication"],
          "steps": [
            {"type": "given", "description": "user has valid credentials"},
            {"type": "when", "description": "user attempts to login"},
            {"type": "then", "description": "user is authenticated"}
          ]
        }
      ]
    }
  ]
}
```

### 2. Generate Skeleton Tests

```bash
specleft test skeleton --features-file features.json --output-dir tests/
```

This generates test files with `@specleft` decorators and step context managers:

```python
from specleft import specleft

@specleft(feature_id="AUTH-001", scenario_id="login-success")
def test_login_success():
    with specleft.step("Given user has valid credentials"):
        pass  # TODO: Implement

    with specleft.step("When user attempts to login"):
        pass  # TODO: Implement

    with specleft.step("Then user is authenticated"):
        pass  # TODO: Implement
```

### 3. Implement Test Logic

Fill in the step implementations:

```python
from specleft import specleft

@specleft(feature_id="AUTH-001", scenario_id="login-success")
def test_login_success(auth_service):
    with specleft.step("Given user has valid credentials"):
        username, password = "admin", "admin123"

    with specleft.step("When user attempts to login"):
        result = auth_service.login(username, password)

    with specleft.step("Then user is authenticated"):
        assert result is True
        assert auth_service.is_authenticated(username)
```

### 4. Run Tests

```bash
pytest
```

Results are automatically saved to `.specleft/results/`.

### 5. Generate Report

```bash
specleft test report --open-browser
```

## Reusable Step Methods

Create reusable step functions that are automatically traced when called from `@specleft` tests:

```python
from specleft import specleft, reusable_step

@reusable_step("User logs in with username '{username}'")
def login_user(auth_service, username: str, password: str) -> bool:
    """Reusable login step with parameter interpolation."""
    return auth_service.login(username, password)

@reusable_step("Verify user '{username}' is authenticated")
def verify_authenticated(auth_service, username: str) -> None:
    """Reusable verification step."""
    assert auth_service.is_authenticated(username)

@specleft(feature_id="AUTH-001", scenario_id="login-success")
def test_login_success(auth_service):
    with specleft.step("Given user has valid credentials"):
        username, password = "admin", "admin123"

    # Reusable steps are automatically traced with interpolated parameters
    result = login_user(auth_service, username, password)

    with specleft.step("Then login succeeded"):
        assert result is True

    verify_authenticated(auth_service, username)
```

## CLI Reference

### `specleft test skeleton`

Generate skeleton test files from a features.json specification.

```bash
specleft test skeleton [OPTIONS]

Options:
  -f, --features-file PATH  Path to features.json (default: features.json)
  -o, --output-dir PATH     Output directory (default: tests)
  --single-file             Generate all tests in one file
```

### `specleft test report`

Generate an HTML report from test results.

```bash
specleft test report [OPTIONS]

Options:
  -r, --results-file PATH   Specific results JSON file (default: latest)
  -o, --output PATH         Output HTML file (default: report.html)
  --open-browser            Open report in browser after generation
```

### `specleft features validate`

Validate a features.json file against the schema.

```bash
specleft features validate [OPTIONS]

Options:
  --file PATH   Path to features.json (default: features.json)
```

## Filtering Tests by Tags

Scenario tags are automatically injected as pytest markers at runtime:

```bash
# Run only smoke tests
pytest -m smoke

# Run authentication tests
pytest -m authentication

# Combine markers
pytest -m "smoke and authentication"
```

## Auto-Skip Orphaned Tests

When a scenario is removed from `features.json`, the corresponding test is automatically skipped with a clear message:

```
SKIPPED [1] test_auth.py: Scenario 'old-scenario' (feature: AUTH-001) not found in features.json
```

This helps identify tests that need to be removed or updated.

## Schema Reference

### features.json Structure

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Schema version (default: "1.0") |
| `features` | array | List of feature objects |

### Feature Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique ID matching `[A-Z0-9-]+` |
| `name` | string | Yes | Human-readable name |
| `description` | string | No | Feature description |
| `metadata` | object | No | Feature-level metadata |
| `scenarios` | array | Yes | List of scenario objects |

### Feature Metadata

| Field | Type | Description |
|-------|------|-------------|
| `owner` | string | Team or person responsible |
| `component` | string | Component name |
| `priority` | string | "critical", "high", "medium", "low" |
| `tags` | array | Feature-level tags |
| `external_references` | array | Links to external systems (Jira, GitHub, etc.) |
| `links` | object | Documentation and other links |
| `custom` | object | Extensible custom fields |

### Scenario Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique ID matching `[a-z0-9-]+` |
| `name` | string | Yes | Human-readable name |
| `description` | string | No | Scenario description |
| `priority` | string | No | "critical", "high", "medium", "low" |
| `tags` | array | No | List of tag strings (become pytest markers) |
| `metadata` | object | No | Scenario-level metadata |
| `steps` | array | Yes | List of step objects |
| `test_data` | array | No | Parameterization data |

### Scenario Metadata

| Field | Type | Description |
|-------|------|-------------|
| `test_type` | string | "smoke", "regression", "integration", "e2e", "performance", "unit" |
| `execution_time` | string | "fast", "medium", "slow" |
| `dependencies` | array | Required services/resources |
| `author` | string | Test author |
| `flaky` | boolean | Mark test as flaky |
| `skip` | boolean | Skip this test |
| `skip_reason` | string | Reason for skipping |
| `custom` | object | Extensible custom fields |

### Step Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | "given", "when", "then", "and" |
| `description` | string | Yes | Step description |
| `metadata` | object | No | Step-level metadata |

### Test Data Object (for Parameterization)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `params` | object | Yes | Parameter key-value pairs |
| `description` | string | No | Description for this data row |

## Parameterized Tests

Define test data in features.json:

```json
{
  "id": "extract-unit-valid",
  "name": "Extract unit from valid input",
  "test_data": [
    {"params": {"input": "10kg", "expected": "kg"}, "description": "Kilograms"},
    {"params": {"input": "5lb", "expected": "lb"}, "description": "Pounds"}
  ],
  "steps": [
    {"type": "when", "description": "extracting unit from '{input}'"},
    {"type": "then", "description": "unit should be '{expected}'"}
  ]
}
```

Generated test:

```python
@specleft(feature_id="PARSE-001", scenario_id="extract-unit-valid")
@pytest.mark.parametrize("input, expected", [
    ("10kg", "kg"),
    ("5lb", "lb"),
])
def test_extract_unit_valid(input, expected):
    with specleft.step(f"When extracting unit from '{input}'"):
        result = extract_unit(input)

    with specleft.step(f"Then unit should be '{expected}'"):
        assert result == expected
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=src/specleft tests/

# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## Project Structure

```
spec-left/
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md
├── examples/
│   ├── features.json
│   └── test_example.py
├── src/
│   └── specleft/
│       ├── __init__.py
│       ├── decorators.py
│       ├── schema.py
│       ├── pytest_plugin.py
│       ├── collector.py
│       ├── cli/
│       │   ├── __init__.py
│       │   └── main.py
│       └── templates/
│           ├── skeleton_test.py.jinja2
│           └── report.html.jinja2
└── tests/
    ├── test_decorators.py
    ├── test_schema.py
    ├── test_collector.py
    ├── test_cli.py
    └── test_pytest_plugin.py
```

## License

MIT
