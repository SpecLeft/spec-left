# SpecLeft SDK - Implementation Progress

## Overview

This document tracks the implementation progress of the SpecLeft SDK. v1 is complete; v2 (Foundation) is tracked via the "Foundation v2" milestone issues. Use `.llm/SpecLeft-v2-iteration.md` as a lookup only when needed to recover details.

## Implementation Phases

### v2 Foundation (In Progress)

Phase tracking is managed in GitHub issues under the "Foundation v2" milestone. Each phase has a feature issue with child story issues:
- Phase 1: Schema & Parser (`https://github.com/SpecLeft/spec-left/issues/16`) - Complete
- Phase 2: CLI Feature Ops (`https://github.com/SpecLeft/spec-left/issues/17`) - Complete
- Phase 3: Decorators & Steps (`https://github.com/SpecLeft/spec-left/issues/18`) - Complete
- Phase 4: Pytest Plugin & Collector (`https://github.com/SpecLeft/spec-left/issues/19`) - Complete (filter selection + report metadata refinements)
- Phase 5: CLI Test Ops (`https://github.com/SpecLeft/spec-left/issues/20`) - Complete
- Phase 6: Test Revision System (`https://github.com/SpecLeft/spec-left/issues/21`) - Complete (spec differ + test sync)
- Phase 7: Docs & Examples (`https://github.com/SpecLeft/spec-left/issues/22`) - Complete

Use `.llm/SpecLeft-v2-iteration.md` only for detailed reference when needed.

## v1 Implementation Phases (Complete)

### Phase 1: Schema Definition (schema.py) ✅ COMPLETE

**Goal:** Define the Markdown spec structure using Pydantic models with generic, extensible metadata.

**Implemented:**
- [x] `StepType` enum (given/when/then/and/but)
- [x] `Priority` enum (critical/high/medium/low)
- [x] `ExecutionTime` enum (fast/medium/slow)
- [x] `SpecStep` model - Individual test step
- [x] `SpecDataRow` model - Parameter data for parameterized tests
- [x] `ScenarioSpec` model - Scenario specification
- [x] `StorySpec` model - Story specification
- [x] `FeatureSpec` model - Feature specification
- [x] `SpecsConfig` model - Root configuration

**Validation:**
- [x] Feature IDs match pattern `^[a-z0-9-]+$`
- [x] Scenario IDs match pattern `^[a-z0-9-]+$` and are unique across specs
- [x] Step descriptions cannot be empty
- [x] Feature IDs are unique across the config
- [x] `SpecsConfig.from_directory()` helper method to load Markdown specs

**Tests:** `tests/test_schema.py` - 39 tests passing

**Success Criteria Met:**
- ✅ Pydantic models validate Markdown spec structure
- ✅ IDs follow v2 naming conventions
- ✅ All metadata fields are optional
- ✅ Clear error messages on validation failures

---

### Phase 2: Decorator Implementation (decorators.py) ✅ COMPLETE

Note: v1 phases below are historical; v2 progress is tracked in milestone issues.

**Goal:** Create the `@specleft` decorator, `specleft.step()` context manager, and `@reusable_step` decorator for reusable step methods.

**Implemented:**
- [x] `@specleft(feature_id, scenario_id)` decorator
- [x] `specleft.step(description)` context manager
- [x] Thread-safe step collection using `threading.local()`
- [x] `StepResult` dataclass for step tracking
- [x] `in_specleft_test` flag tracking (for reusable step detection)
- [x] `@reusable_step(description)` decorator for reusable step methods
- [x] Parameter interpolation in descriptions (e.g., `"User logs in with {username}"`)
- [x] Helper functions: `get_current_steps()`, `clear_steps()`, `is_in_specleft_test()`

**Tests:** `tests/test_decorators.py` - 38 tests passing

**Success Criteria Met:**
- ✅ `@specleft` decorator stores feature_id and scenario_id on functions
- ✅ `specleft.step()` context manager records step execution with timing
- ✅ `@reusable_step` decorator traces calls only inside `@specleft` tests
- ✅ Parameter interpolation works with function arguments
- ✅ Thread-safe implementation using `threading.local()`
- ✅ Proper exception handling and propagation

---

### Phase 3: Pytest Plugin (pytest_plugin.py) ✅ COMPLETE

**Goal:** Integrate with pytest to collect test metadata, results, auto-skip removed scenarios, and inject markers from tags.

**Implemented:**
- [x] `pytest_configure` hook - Initializes result collection and registers markers
- [x] `pytest_collection_modifyitems` hook - Collects @specleft decorated tests
- [x] `pytest_runtest_makereport` hook - Captures test results and steps
- [x] `pytest_sessionfinish` hook - Saves results to disk
- [x] Auto-skip tests for removed scenarios with clear skip message
- [x] Runtime marker injection from scenario tags (makes tests filterable with `pytest -m <tag>`)
- [x] Multiple specs search paths (current dir, examples/, rootdir)
- [x] Graceful handling of missing/invalid specs (warning only, tests still run)

**Tests:** `tests/test_pytest_plugin.py` - 28 tests passing

**Success Criteria Met:**
- ✅ Basic pytest hooks collect @specleft decorated tests
- ✅ Tests are auto-skipped if scenario not in specs with clear message
- ✅ Scenario tags are injected as pytest markers at runtime
- ✅ Tests can be filtered with `pytest -m <tag>`
- ✅ Missing specs logs warning but tests still run
- ✅ Results are saved to `.specleft/results/` after session

---

### Phase 4: Result Collector (collector.py) ✅ COMPLETE

**Implemented:**
- [x] `ResultCollector` class
- [x] Group results by feature/scenario
- [x] Summary statistics calculation
- [x] JSON output to `.specleft/results/`

---

### Phase 5: CLI - Skeleton Generation (cli/main.py) ✅ COMPLETE

**Goal:** Create CLI commands to generate skeleton tests from specs.

**Implemented:**
- [x] Click CLI framework with resource-based command structure
- [x] `specleft test skeleton` command
- [x] `specleft features validate` command
- [x] Jinja2 template for skeleton test generation (`skeleton_test.py.jinja2`)
- [x] Custom filters (`snake_case`, `repr`) for template rendering
- [x] Single-file mode (`--single-file`) or per-feature file generation
- [x] Custom features file path (`--features-file`, `-f`)
- [x] Custom output directory (`--output-dir`, `-o`)

**Tests:** `tests/test_cli.py` - 32 tests passing

**Success Criteria Met:**
- ✅ `specleft test skeleton` generates test stubs from specs
- ✅ `specleft features validate` validates specs schema
- ✅ Generated tests use `@specleft` decorator with correct IDs
- ✅ Parameterized tests are generated correctly with `@pytest.mark.parametrize`
- ✅ Step context managers are included with `pass` statements
- ✅ Clear error messages on validation failures

---

### Phase 6: CLI - Report Generation ✅ COMPLETE

**Goal:** Generate HTML reports from collected test results.

**Implemented:**
- [x] `specleft test report` command
- [x] HTML report template (`report.html.jinja2`)
- [x] Auto-detection of latest results file
- [x] Specific results file path (`--results-file`, `-r`)
- [x] Custom output path (`--output`, `-o`)
- [x] Open in browser option (`--open-browser`)
- [x] Summary dashboard (pass/fail counts, duration)
- [x] Feature/scenario breakdown with step details
- [x] Error message display
- [x] Responsive CSS styling (inline, no external dependencies)

**Success Criteria Met:**
- ✅ `specleft test report` generates HTML from results JSON
- ✅ Report shows summary, features, scenarios, and steps
- ✅ Color coding (green=pass, red=fail, yellow=skip)
- ✅ Self-contained HTML with inline CSS

---

### Phase 7: Examples & Documentation ✅ COMPLETE

**Goal:** Create working examples and comprehensive documentation.

**Implemented:**
- [x] `examples/features/` - Comprehensive example with 2 features, 5 scenarios using generic metadata
- [x] `examples/test_example.py` - Full example demonstrating:
  - Regular tests with step context managers
  - Parameterized tests with `@pytest.mark.parametrize`
  - Reusable step methods with `@reusable_step`
  - Parameter interpolation in step descriptions
- [x] `README.md` - Complete documentation with:
  - Project description and feature highlights
  - Installation instructions
  - Quick start guide with examples
  - Reusable step methods documentation
  - CLI command reference
  - Tag filtering and auto-skip documentation
  - Complete schema reference
  - Development setup instructions
- [x] `CONTRIBUTING.md` - Contributor guide with:
  - Development setup instructions
  - Running tests guide
  - Code style guidelines
  - Project structure overview
  - Commit message guidelines

**Success Criteria Met:**
- ✅ Working examples demonstrating all major features
- ✅ Comprehensive README.md with usage instructions
- ✅ CONTRIBUTING.md with development setup
- ✅ All example tests pass (7 tests)
- ✅ No references to "shiftleft" remaining

---

### Phase 8: Unit Tests ✅ COMPLETE

**Completed:**
- [x] `tests/test_schema.py` - 39 tests
- [x] `tests/test_decorators.py` - 38 tests
- [x] `tests/test_pytest_plugin.py` - 28 tests
- [x] `tests/test_cli.py` - 32 tests
- [x] `tests/test_collector.py` - 24 tests

**Total Tests:** 161 passing

**Success Criteria Met:**
- ✅ All modules have comprehensive test coverage
- ✅ All tests pass with no failures
- ✅ Edge cases and error conditions tested

---

## Notes

- All references to "shiftleft" have been renamed to "specleft"
- Package name: `spec-left` (PyPI), import name: `specleft`
- CLI command: `specleft`

## Next Steps

1. ~~Complete Phase 2 (reusable step methods)~~ ✅ DONE
2. ~~Complete Phase 3 (auto-skip, marker injection)~~ ✅ DONE
3. ~~Update CLI command structure (Phase 5)~~ ✅ DONE
4. ~~Create templates~~ ✅ DONE
5. ~~Complete Phase 6 (report generation)~~ ✅ DONE
6. ~~Update documentation (Phase 7)~~ ✅ DONE
7. ~~Write remaining tests (test_collector.py)~~ ✅ DONE

**All phases complete!** The SpecLeft SDK is ready for use for v1.
