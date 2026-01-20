# SpecLeft SDK - Implementation Progress

## Overview

This document tracks the implementation progress of the SpecLeft SDK. v1 is complete; v2 (Foundation) is tracked via the "Foundation v2" milestone issues. Use `.llm/implementation-spec.md` as a lookup only when needed to recover details.

## Implementation Phases

### Phase 1: CLI Enhancements (Doctor/Status/Next) ✅ COMPLETE

**Goal:** Add diagnostic and workflow commands for agents.

**Implemented:**
- `specleft doctor` with table/json output and dependency checks
- `specleft status` with filters and implementation coverage
- `specleft next` for priority-driven next-test selection
- CLI tests for doctor/status/next commands

---

### Phase 2: CLI Enhancements (Coverage/Init/Skeleton) ✅ COMPLETE

**Goal:** Add coverage reporting, initialization, and improved skeleton planning.

**Implemented:**
- `specleft coverage` with table/json/badge output and thresholds
- `specleft init` for example and blank setup with dry-run support
- `specleft test skeleton` with dry-run, json output, force overwrite, and new confirmation flow
- CLI tests for coverage/init/skeleton updates

---

### Phase 3: CLI Enhancements (JSON + Contract) 🚧 IN PROGRESS

**Goal:** Add JSON output across remaining commands and implement agent contract checks.

**In progress:**
- Adding `--format json` for `specleft features list`, `features stats`, `features validate`, and `test report`
- Implementing `specleft contract` and `specleft contract test`
- Updating CLI tests for new JSON outputs and contract commands
- Refactoring CLI into `src/specleft/commands/` modules with shared logic moved to `src/specleft/utils/` (in progress: created `commands/` and `utils/` packages; started contract command extraction)

---

## v1 Foundation (Complete)



### Phase 6: CLI - Report Generation ✅ COMPLETE

**Goal:** Generate HTML reports from collected test results.

**Implemented:**

---

## Notes

- Started CLI refactor into `src/specleft/commands/` and `src/specleft/utils/`.
- Added new modules: `commands/__init__.py`, `commands/constants.py`, `commands/contract.py`, `commands/formatters.py`, `commands/types.py`, `commands/cli_access.py`, `commands/contracts/{types.py,payloads.py,table.py,utils.py,runner.py}`, `utils/{text.py,filesystem.py}`.
- Contract payload moved to `commands/contracts/payloads.py` and aligned with original schema (exit codes, docs path). `commands/contract.py` now wires `contract` and `contract test`.
- `commands/formatters.py` still shows an LSP "(" warning; re-check if tooling complains.
- `commands/contracts/runner.py` now calls `get_cli()` from `commands/cli_access.py` and uses helpers from `commands/contracts/utils.py`.
- Remaining work: split `cli/main.py` into modules for `features`, `test`, `status`, `next`, `coverage`, `doctor`, `init`; update imports in `tests/test_cli.py` (to use `specleft.utils.text.to_snake_case`); rewire `cli/main.py` to attach groups from `specleft.commands`.
- After moving code, update references to `_format_*` helpers to use `commands/formatters.py` and align contract table lookups with payload schema.
- Run `pytest` after wiring to confirm CLI still works.

## Next Steps


