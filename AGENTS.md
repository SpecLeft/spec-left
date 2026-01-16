# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

See `.llm/instructions.md` for the instruction profile (Senior Python Engineer persona and working style).

## Project Overview

SpecLeft SDK is a Python test management library for pytest. It decorates tests with metadata, collects results with step-by-step granularity, generates skeleton tests from JSON specs, and produces HTML reports.

**Status:** Early prototype - see `.llm/specleft_design.md` for full specification.

## Commands

```bash
pip install -e ".[dev]"              # Install with dev dependencies
pytest                                # Run all tests
pytest tests/test_schema.py::test_name  # Run single test
pytest --cov=src/specleft tests/     # Run with coverage
black src/ tests/                     # Format code
ruff check src/ tests/                # Lint
mypy src/                             # Type check

# CLI (after implementation)
specleft test skeleton                # Generate test stubs from features.json
specleft test report                  # Generate HTML report from results
specleft features validate            # Validate features.json schema
```

## Architecture

```
features.json → schema.py (validate) → cli skeleton → test files with @specleft
                                                              ↓
                                                        pytest runs
                                                              ↓
HTML report ← cli report ← collector.py ← pytest_plugin.py (hooks)
```

**schema.py** - Pydantic models for features.json (FeaturesConfig, Feature, Scenario, TestStep, and metadata classes)

**decorators.py** - `@specleft(feature_id, scenario_id)` decorator and `specleft.step()` context manager. Uses `threading.local()` for parallel test safety.

**pytest_plugin.py** - Hooks for test collection and result capture. Registered via entry point.

**collector.py** - Groups results by feature/scenario, writes to `.specleft/results/`

**cli/main.py** - Click CLI with `test skeleton`, `test report`, and `features validate` commands

**templates/** - Jinja2 templates for test generation and HTML reports

## Implementation Order

Follow the v2 Foundation milestone issues ("Foundation v2") as the source of truth for next steps. Use `.llm/SpecLeft-v2-iteration.md` only as a lookup when details are needed or context is missing.

See `PROGRESS.md` for current implementation status.

## V2 Foundation Status

GitHub issues (features + stories) track the v2 foundation phases. Start with Phase 1 and follow the parent/child issue links:
- Phase 1: Schema & Parser (`https://github.com/SpecLeft/spec-left/issues/16`)
- Phase 2: CLI Feature Ops (`https://github.com/SpecLeft/spec-left/issues/17`)
- Phase 3: Decorators & Steps (`https://github.com/SpecLeft/spec-left/issues/18`)
- Phase 4: Pytest Plugin & Collector (`https://github.com/SpecLeft/spec-left/issues/19`)
- Phase 5: CLI Test Ops (`https://github.com/SpecLeft/spec-left/issues/20`)
- Phase 6: Test Revision System (`https://github.com/SpecLeft/spec-left/issues/21`)
- Phase 7: Docs & Examples (`https://github.com/SpecLeft/spec-left/issues/22`)

## Conventions

- Python 3.10+ with type hints
- Use `pathlib` for file operations
- Feature IDs: `[A-Z0-9-]+`, Scenario IDs: `[a-z0-9-]+`
