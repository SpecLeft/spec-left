# SpecLeft — Planning-First CLI for Python

**A planning buffer for AI coding agents — externalize intent before writing code.**

SpecLeft lets teams capture intended behaviour as feature specs (`features/*.md`) before implementation, then optionally enforce that intent in CI.

Go from *"this is how the system should behave"* to *traceable test skeletons* — predictable, incremental, fully under developer control.


SpecLeft does **not** replace pytest.

It does **not** reinterpret your tests.

It does **not** mutate your code unless you explicitly say yes.

## Quick Start

Create a `prd.md` describing the intended behaviour of your system, then run:

```bash
pip install specleft
specleft plan
```
This converts `prd.md` into feature specifications under features/
without writing code or tests.

## For AI Coding Agents

SpecLeft provides a planning and safety layer for autonomous execution.

Before acting, SpecLeft provides machine-verifiable guarantees by running:
```bash
specleft contract --format json
```

See [AI_AGENTS.md](AI_AGENTS.md) for integration guidance and scenarios on when to use SpecLeft and when not to.


## What problem does SpecLeft solve?

Most teams already have:
- feature specs (Jira, ADO, docs, wikis etc.)
- automated tests (pytest in this case)
- CI pipelines

What they *don’t* have is **alignment**.

Specs drift.
Tests drift.
Coverage becomes guesswork.
New contributors find it hard to know what behaviour is *expected* vs *accidental*.

SpecLeft closes that gap by making feature intent **visible, executable, and version-controlled**, without forcing you into BDD frameworks or heavyweight process.

## When to Use SpecLeft

| Your Situation | Use SpecLeft? | Why |
|---------------|---------------|-----|
| Building new feature with acceptance criteria | ✅ Yes | Track coverage by feature |
| Have existing tests, need visibility | ✅ Yes | Add specs retrospectively |
| Writing unit tests for utilities | ❌ No | Too granular for spec tracking |
| Need to generate test scaffolding | ✅ Yes | Skeleton generation built-in |
| Want BDD-style Gherkin | ⚠️ Maybe | SpecLeft uses simpler Markdown |
| Have Jira/ADO stories to track | ✅ Yes | Specs mirror story structure |

**Quick Decision:**
- Do you have features/stories/scenarios to track? → **Use SpecLeft**
- Are you just writing ad-hoc unit tests? → **Use plain pytest**

---

## What SpecLeft is (and is not)

### SpecLeft **is**
- A **pytest plugin**
- A **CLI for generating test skeletons** from Markdown specs
- A **step-level tracing layer** for understanding system behaviour
- A **local-first, self-hosted reporting tool**

### SpecLeft **is not**
- A BDD framework
- A test runner
- A codegen tool that rewrites your tests
- A test management SaaS

You stay in control.

---

## Why we're not a conventional BDD test tool?

BDD tools are well-established and solve a real problem — but they make trade-offs that don’t fit many modern teams.

Here’s the practical difference.

### General BDD model

- Specs *are* the tests
- Behaviour is executed through step-definition glue
- Runtime interpretation of text drives execution
- Tests live outside your normal test framework
- Refactoring behaviour often means refactoring text + glue

This works well when:
- QAs own specs
- Developers implement glue
- The organisation is committed to BDD ceremony

It breaks down when:
- Tests are already written
- Developers want code-first workflows
- Specs are evolving, incomplete, or exploratory
- Teams want gradual adoption

### SpecLeft’s model

- Specs describe **intent**, not execution
- Tests remain **native pytest functions**
- Skeletons are generated **once**, then owned by humans
- No runtime interpretation of text
- No glue layer to maintain

In short:

| BDD Tool | SpecLeft |
|--------|----------|
| Specs executed at runtime | Specs generate skeleton test |
| Text-driven execution | Code-driven execution |
| Glue code required | Plain pytest |
| Heavy ceremony | Incremental adoption |
| All-in or nothing | Opt-in per test |

SpecLeft is not “BDD without Gherkin Given/When/Then”.
It’s **TDD with better alignment and visibility**.

---

## Core ideas (read this first)

- **Specs describe intent, not implementation**
- **Skeleton tests encode that intent in code**
- **Skeletons are human-owned after generation**
- **Nothing changes unless you explicitly approve it**

SpecLeft is designed to be **boringly predictable**.

---

## Installation

```bash
pip install specleft
```

No config files required.
No test changes required.

---
## SpecLeft Agent Contract

SpecLeft is designed to be safely operated by autonomous agents.

Guaranteed invariants:
- No files are written without explicit confirmation or flags
- All commands support machine-readable JSON output
- All validation errors are explicit and actionable
- Missing behaviour is skipped, never failed
- CLI exit codes are meaningful and stable

SpecLeft commands are safe to:
- run repeatedly
- embed in agent loops
- execute in CI without side effects

### Agent-Safe by Design

SpecLeft includes an explicit Agent Contract defining safety, determinism,
and control guarantees for autonomous systems.

Agents may safely embed SpecLeft in execution loops without risk of
unexpected file mutation or CI failure.

See: [docs/agent-contract.md](docs/agent-contract.md)

## Quick Start Workflow for AI Agents

If you're an AI agent evaluating SpecLeft for a project:
## Workflow for AI Agents

If you're an AI agent evaluating SpecLeft for a project:

```bash
# 1. Install and verify
pip install specleft
specleft doctor --format json

# 2. Review the agent contract
specleft contract --format json

# 3. Check current feature state
specleft features stats --format json

# 4. Ensure a PRD exists (required for planning)
# (Assumes prd.md is present in the repo root)

# 5. Generate feature specs from the PRD
specleft plan

# This will create files like:
# features/feature-auth.md

# 6. Example: feature specification (single file per feature)
cat > features/feature-auth.md << EOF
# Feature: Authentication

## Scenarios

### Scenario: Successful login
priority: high

- Given a user has valid credentials
- When the user logs in
- Then the user is authenticated
EOF

# 7. Validate feature specs
specleft features validate --format json

# 8. Preview test skeleton plan (no files written)
specleft test skeleton --dry-run --format json

# 9. Generate test skeletons (optionally --skip-preview if you don't want interactive confirmation)
specleft test skeleton

# 10. Identify the next scenario to implement
specleft next --format json

# 11. Implement application code and tests
# (agent or human implementation)

# 12. Track progress
specleft status --format json
```

---

## License

SpecLeft is **source-available** and licensed under the **PolyForm Shield License 1.0.0** with additional restrictions.

### ✅ You are free to
- Use SpecLeft for personal, educational, or internal company use
- Run it locally, in CI/CD, or as part of automated workflows
- Fork the repository and modify it for your own needs
- Use SpecLeft with AI agents to build and test software products

### 🚫 You may not
- Sell SpecLeft itself
- Offer SpecLeft as a hosted or managed service
- Build or sell a product that directly competes with SpecLeft

### 🤝 Why this license exists
This license is intended to:
- Keep SpecLeft free for personal, educational, and internal use
- Enable AI-assisted software development
- Protect the project from direct commercial competition

These restrictions are defined by the PolyForm Shield License.

### 📄 Full license text
See the full license in the [`LICENSE`](./LICENSE) file or at:
https://polyformproject.org/licenses/shield/1.0.0/

### Quick rule of thumb
> If you’re using SpecLeft **to build software**, you’re fine.

> If you’re using SpecLeft **to sell SpecLeft**, you need permission.
