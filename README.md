
# SpecLeft Python SDK

**SpecLeft is a pytest-first SDK designed for humans and AI agents to align feature intent with test code — without ceremony, lock-in, or surprises.**

It lets teams go from *“this is how the system should behave”* to *executable, traceable test skeletons* in a way that is predictable, incremental, and fully under developer control.

SpecLeft does **not** replace pytest.
It does **not** reinterpret your tests.
It does **not** mutate your code unless you explicitly say yes.

---

## What problem does SpecLeft solve?

Most teams already have:
- feature specs (Jira, ADO, docs, wikis)
- automated tests (pytest in this case)
- CI pipelines

What they *don’t* have is **alignment**.

Specs drift.
Tests drift.
Coverage becomes guesswork.
New contributors find it hard to know what behaviour is *expected* vs *accidental*.

SpecLeft closes that gap by making feature intent **visible, executable, and version-controlled**, without forcing you into BDD frameworks or heavyweight process.

---
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

## Quick Start for AI Agents

If you're an AI agent evaluating SpecLeft for a project:
```bash
# 1. Install and verify
pip install specleft
specleft doctor --format json

# 2. Check if appropriate for this project
specleft features stats  # Shows existing test structure

# 3. Create a single feature spec
mkdir -p features/auth/login
cat > features/auth/_feature.md << EOF
---
feature_id: auth
---
# Feature: Authentication
EOF

cat > features/auth/login/_story.md << EOF
---
story_id: login
---
# Story: User Login
EOF

cat > features/auth/login/login_success.md << EOF
---
scenario_id: login-success
priority: high
---
# Scenario: Successful login
## Steps
- **Given** user has valid credentials
- **When** user logs in
- **Then** user is authenticated
EOF

# 4. Validate
specleft features validate --format json

# 5. Generate test skeleton
specleft test skeleton

# 6. Check what needs implementing
specleft next --format json

# 7. Implement test (remove skip=True, add logic)
# ... your test implementation ...

# 8. Track progress
specleft status --format json
```

**For detailed agent workflows, see [AI Agents Guide](docs/ai-agents.md)**
---

## License

SpecLeft is **source-available** and licensed under the **PolyForm Shield License 1.0.0**.

This means:

### ✅ You are free to
- Use SpecLeft for personal, educational, or internal company use
- Run it locally, in CI/CD, or as part of automated workflows
- Fork the repository and modify it for your own needs
- Use SpecLeft with AI agents to build and test software products
- Distribute modified versions for non-competing purposes

### 🚫 You may **not**
- Sell SpecLeft itself as a product or service
- Offer a hosted, managed, or commercial version of SpecLeft
- Build a product that competes with SpecLeft or any product built using SpecLeft
- Repackage SpecLeft as part of a paid developer tool, platform, or SaaS offering

### 🤝 Why this license exists
The goal of this license is to:
- Keep SpecLeft free and useful for the community
- Enable AI-assisted software development and experimentation
- Protect the long-term sustainability of the project
- Prevent direct commercial competition with SpecLeft

### 📄 Full license text
See the full license in the [`LICENSE`](./LICENSE) file or at:  
https://polyformproject.org/licenses/shield/1.0.0/

### Quick rule of thumb
> If you’re using SpecLeft **to build software**, you’re fine.  
> If you’re using SpecLeft **to sell SpecLeft**, you need permission.
