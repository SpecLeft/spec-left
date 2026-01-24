# SpecLeft Agent Contract

**Version:** 1.0
**Applies to:** SpecLeft CLI ≥ 0.2.0

This document defines the **operational guarantees** that SpecLeft provides to autonomous agents and automated systems.

SpecLeft is designed to be safely embedded in agent execution loops.

---

## 1. Safety Guarantees (Hard)

SpecLeft guarantees that:

- **No files are created, modified, or deleted** without:
  - explicit interactive confirmation, **or**
  - an explicit destructive flag (e.g. `--force`)
- `--dry-run` **never writes to disk**, under any circumstances
- Existing test files are **never modified** unless explicitly overwritten
- SpecLeft does **not** mutate:
  - application source code
  - configuration files
  - environment state
  - dependency manifests

These guarantees are invariant.

---

## 2. Execution Guarantees

SpecLeft guarantees that:

- Skeleton tests are **always skipped by default**
- Skipped scenarios **never cause test failures**
- Missing implementations are **explicitly reported**, never inferred
- Spec validation failures are **non-destructive**
- Spec validation **does not block execution** unless explicitly enforced

SpecLeft will never cause CI failure unless configured to do so.

---

## 3. Determinism & Idempotence

SpecLeft guarantees that:

- CLI commands are **deterministic** for the same inputs
- Commands may be **re-run safely**
- Re-running commands does not introduce additional side effects
- Output ordering is stable unless explicitly documented otherwise

SpecLeft is safe to execute in retry loops.

---

## 4. CLI as API Guarantees

SpecLeft guarantees that:

- All commands support `--format json`
- JSON output is:
  - machine-readable
  - schema-consistent
  - free of human-only formatting
- JSON fields are **additive within a minor version**
- Breaking changes occur only on major version increments

Agents may rely on documented JSON fields without defensive parsing.

### Example output (JSON)

```bash
❯ specleft contract --format json
```
```json
{
  "contract_version": "1.0",
  "specleft_version": "0.2.0",
  "guarantees": {
    "safety": {
      "no_implicit_writes": true,
      "dry_run_never_writes": true,
      "existing_tests_not_modified_by_default": true
    },
    "execution": {
      "skeletons_skipped_by_default": true,
      "skipped_never_fail": true,
      "validation_non_destructive": true
    },
    "determinism": {
      "deterministic_for_same_inputs": true,
      "safe_for_retries": true
    },
    "cli_api": {
      "json_supported_globally": true,
      "json_additive_within_minor": true,
      "exit_codes": {
        "success": 0,
        "error": 1,
        "cancelled": 2
      }
    }
  },
  "docs": {
    "agent_contract": "docs/agent-contract.md"
  }
}
```

---

## 5. Exit Code Semantics

SpecLeft uses stable exit codes:

| Exit Code | Meaning |
|---------:|--------|
| `0` | Success |
| `1` | Error, validation failure, or threshold breach |
| `2` | Explicit user or agent cancellation |

Exit codes are reliable and intentional.

---

## 6. Control Boundaries (Non-Negotiable)

SpecLeft guarantees that it:

- Does **not** infer or generate test logic
- Does **not** rewrite existing tests
- Does **not** interpret specs at runtime
- Does **not** execute application code
- Does **not** manage environments, secrets, or credentials

SpecLeft describes intent — it never guesses behavior.

---

## 7. Coverage Semantics

SpecLeft guarantees that:

- Coverage reflects **spec-to-test alignment only**
- Coverage does **not** represent code coverage
- Coverage is computed from observable, explicit links
- Threshold enforcement is **opt-in**

Coverage metrics are transparent and reproducible.

---

## 8. Agent-Safe Defaults

SpecLeft defaults are designed for autonomous execution:

- Read-only behavior unless explicitly authorized
- Safe no-op on incomplete input
- Clear reporting of missing work
- No hidden automation

Agents are always in control.

---

## 9. Non-Goals (Explicit)

SpecLeft explicitly does **not**:

- Auto-implement tests
- Auto-fix failing tests
- Enforce process or workflow
- Replace pytest
- Act as a test runner
- Act as a SaaS or remote service

These behaviors will not be added implicitly.

---

## 10. Contract Stability

This contract applies to all minor and patch releases within the same major version.

Changes to this contract require:
- explicit documentation
- a major version increment

---
## Verification Caching

   Safe to cache verification results for:
   - Same `specleft_version`
   - Same `contract_version`
   - Within same session

   Re-verify if:
   - SpecLeft version changes
   - Contract version changes
   - New session starts
---

## Summary for Agents

SpecLeft is:

- **Predictable**
- **Non-destructive**
- **Deterministic**
- **Explicit**
- **Safe for autonomous planning and execution**

SpecLeft may be treated as a **trusted control surface**.
