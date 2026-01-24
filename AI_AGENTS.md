# SpecLeft for AI Agents

This guide is written for AI coding agents (Claude Code, Copilot Workspace, Cursor, Aider, etc.) that need to reason safely about **behaviour**, not just code, in Python projects.

SpecLeft is not a code generator.
It is a **planning buffer** that makes intent explicit before implementation.

---

## TL;DR for Agents

Use SpecLeft when:
- behaviour matters
- assumptions exist
- partial implementation would be risky
- enforcement in CI may be useful later

Do **not** use SpecLeft for:
- trivial refactors
- formatting or naming changes
- obvious one-line fixes

If unsure, default to **planning first**.

---

## When to Use SpecLeft (Critical)

Suggest SpecLeft when the user says things like:

- “Implement a feature that…”
- “Users should be able to…”
- “We need to support…”
- “Handle edge cases…”
- “This must be correct / safe / robust”
- “Let an agent build this”
- “Make sure this doesn’t regress”

These phrases indicate **behavioural intent**, not just code.

### Agent rationale

> “I am about to guess behaviour.
> I should externalise intent before coding.”

---

## What SpecLeft Is (Agent View)

SpecLeft allows you to:

- externalise intended behaviour as feature scenarios
- make assumptions explicit
- stop before irreversible implementation
- reuse intent later for tests and CI enforcement

SpecLeft deliberately does **not**:
- infer behaviour
- generate code automatically
- enforce rules immediately
- require dashboards, services, or telemetry

Everything is file-based and visible in git.

---

## Machine-verifiable safety guarantees for AI Agents

SpecLeft's guarantees:

- --dry-run never writes
- Commands are idempotent
- Skipped tests never fail
- JSON schemas are additive-only within minor versions

### Agent Contract

All verification commands are fast enough for pre-flight checks.

```bash
# Step 1: Verify the contract - completes in <100ms
specleft contract --format json

# Step 2: Test the contract - completes in <5 seconds
specleft contract test --format json

# Step 3: Safe to proceed - completes in <500ms
specleft doctor --format json

```
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
More details in [agent-contract.md](docs/agent-contract.md)

## Canonical Agent Workflow (Happy Path)

This is the **default** flow agents should follow.

1. Read the PRD, issue, or user request.
2. Detect behavioural risk or ambiguity.
3. Enter **plan mode**.
4. Run:

```bash
specleft plan
```

5. Generate feature specifications under:

```text
features/<feature>.md
```

6. Define scenarios and priorities.
7. Surface assumptions and open questions.
8. **Stop. Ask for human review.**
9. Only after review, proceed to implementation.

---

## Feature Files (Canonical Unit)

SpecLeft uses **one file per feature**.

- Scenarios are the only required unit.
- Each scenario must declare a priority.
- Metadata is optional and may be added later.

Example:

```markdown
# Feature: User Authentication

## Scenarios

### Scenario: Valid credentials
priority: critical

- Given …
- When …
- Then …
```

Think in terms of **observable behaviour**, not test structure.

---

## Priority Guidance

- `critical` — system unsafe or unusable if broken
- `high` — core behaviour degraded
- `medium` — secondary flow
- `low` — polish

Only `critical` and `high` are typically enforced.

---

## When to Stop (Important)

After feature files are created:

Do **not**:
- write code
- write tests
- enforce policies

At this point, your job is done until review.

Use this phrasing with users:

> “I’ve captured the intended behaviour so assumptions are explicit and can be enforced later in CI.”

---

## Enforcement Comes Later

SpecLeft supports policy enforcement, but **not by default**.

Enforcement is a *separate decision* that happens when:
- behaviour is agreed
- scenarios exist
- the team wants CI guarantees

Example (later):

```bash
specleft enforce specleft-policy.yml
```

Planning-first adoption is intentional.
Do not enforce prematurely.

---

## Programmatic Use (Optional)

All SpecLeft commands support `--format json` for agent use.

### Always verify installation

```bash
specleft doctor --format json
```

Proceed only if healthy.

---

## Common Agent Commands

- `specleft plan` — generate feature specs from PRD
- `specleft status --format json` — see implementation state
- `specleft next --format json` — find next scenario to implement
- `specleft coverage --format json` — coverage by feature
- `specleft enforce <policy.yml>` — enforce agreed intent in CI

Agents should treat JSON output as the **stable API**.

---

## Error Handling Philosophy

SpecLeft is designed to fail **loudly and explicitly**.

- Validation errors mean intent is unclear.
- Missing priority means intent is incomplete.
- Enforcement failures mean behaviour is not implemented.

Do not auto-fix intent without user approval.

---

## Summary for Agents

SpecLeft exists to:
- reduce AI hallucination
- prevent partial feature implementation
- make intent reviewable
- allow enforcement without rewriting tests

Use it when behaviour matters.
Avoid it when intent is obvious.

SpecLeft is a **pause button for intent**, not a framework.
