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

### 1. Define Features (Markdown specs)

Create Markdown specs under `features/`:

```text
features/
└── auth/
    ├── _feature.md
    └── login/
        ├── _story.md
        └── login_success.md
```

Example `_feature.md`:

```markdown
---
feature_id: auth
component: authentication
owner: auth-team
priority: critical
tags: [smoke]
---

# Feature: User Authentication

Users can securely log in and out of the system.
```

Example `_story.md`:

```markdown
---
story_id: login
priority: high
tags: [authentication]
---

# Story: Login

Login scenarios for authenticated users.
```

Example scenario file:

```markdown
---
scenario_id: login-success
priority: critical
tags: [smoke, authentication]
execution_time: fast
---

# Scenario: Successful login with valid credentials

## Steps
- **Given** user has valid credentials
- **When** user attempts to login
- **Then** user is authenticated
```

### 2. Generate Skeleton Tests

```bash
specleft test skeleton --features-dir features --output-dir tests/
```

This generates test files with `@specleft` decorators and step context managers:

```python
from specleft import specleft

@specleft(feature_id="auth", scenario_id="login-success")
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

@specleft(feature_id="auth", scenario_id="login-success")
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

@specleft(feature_id="auth", scenario_id="login-success")
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

Generate skeleton test files from Markdown specs.

```bash
specleft test skeleton [OPTIONS]

Options:
  -f, --features-dir PATH   Path to features directory (default: features)
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

Validate Markdown specs against the schema.

```bash
specleft features validate [OPTIONS]

Options:
  --dir PATH   Path to features directory (default: features)
```

### `specleft features list`

List features, stories, and scenarios.

```bash
specleft features list [OPTIONS]

Options:
  --dir PATH   Path to features directory (default: features)
```

### `specleft features stats`

Show aggregate statistics for Markdown specs.

```bash
specleft features stats [OPTIONS]

Options:
  --dir PATH   Path to features directory (default: features)
```

## Filtering Tests by Tags

Scenario tags are automatically injected as pytest markers at runtime (from Markdown specs):

```bash
# Run only smoke tests
pytest -m smoke

# Run authentication tests
pytest -m authentication

# Combine markers
pytest -m "smoke and authentication"
```

## Auto-Skip Orphaned Tests

When a scenario is removed from the `features/` specs, the corresponding test is automatically skipped with a clear message:

```
SKIPPED [1] test_auth.py: Scenario 'old-scenario' (feature: AUTH-001) not found in features specs
```

This helps identify tests that need to be removed or updated.

## Schema Reference

### Markdown Specs Structure

SpecLeft v2 expects a `features/` directory with:

- `features/<feature>/_feature.md` for feature metadata
- `features/<feature>/<story>/_story.md` for story metadata
- `features/<feature>/<story>/<scenario>.md` for scenarios

Scenario files include frontmatter plus `## Steps` and optional `## Test Data`.

### Spec Structure

| Section | Description |
|---------|-------------|
| Feature frontmatter | `feature_id`, `component`, `owner`, `priority`, `tags` |
| Story frontmatter | `story_id`, `priority`, `tags` |
| Scenario frontmatter | `scenario_id`, `priority`, `tags`, `execution_time` |
| `## Steps` | BDD steps like `Given/When/Then/And/But` |
| `## Test Data` | Optional Markdown table for parameterized tests |

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

Define test data in Markdown scenario files:

```markdown
---
scenario_id: extract-unit-valid
priority: medium
tags: [parsing]
execution_time: fast
---

# Scenario: Extract unit from valid input

## Test Data
| input | expected | description |
|-------|----------|-------------|
| 10kg | kg | Kilograms |
| 5lb | lb | Pounds |

## Steps
- **When** extracting unit from '{input}'
- **Then** unit should be '{expected}'
```

Generated test:

```python
@specleft(feature_id="parse", scenario_id="extract-unit-valid")
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
├── features/
│   └── ...
├── examples/
│   └── test_example.py
├── src/
│   └── specleft/
│       ├── __init__.py
│       ├── decorators.py
│       ├── schema.py
│       ├── parser.py
│       ├── validator.py
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
    ├── test_parser.py
    ├── test_collector.py
    ├── test_cli.py
    └── test_pytest_plugin.py
```

## License

MIT
