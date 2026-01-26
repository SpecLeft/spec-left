# Getting Started with SpecLeft

This guide walks you through the **15-minute path** — the fastest way to understand what SpecLeft does and whether it fits your workflow.

By the end of this guide, you will:
> - Generate feature specs from a PRD
> - See how intent maps to test skeletons
> - Understand how SpecLeft makes missing behaviour visible

No configuration required. No surprises.

---

## Install SpecLeft

```bash
pip install specleft
```

Verify installation:

```bash
specleft doctor
```

SpecLeft is passive by default — it won't modify anything until you ask.

---

## 1. Write a PRD

Create a `prd.md` file in your repository root:

```markdown
# My Project

## Feature: User Authentication

Users need to log in securely.

### Scenario: Successful login
- Given user has valid credentials
- When user submits login form
- Then user is authenticated and redirected to dashboard

### Scenario: Invalid credentials
- Given user has invalid credentials
- When user submits login form
- Then an error message is displayed

## Feature: Password Reset

Users need to recover forgotten passwords.

### Scenario: Request password reset
- Given user has a registered email
- When user requests password reset
- Then a reset link is sent to their email
```

**Notes:**
- `## Feature:` headings define feature boundaries
- `### Scenario:` headings define individual behaviours
- Steps use Given/When/Then format
- This is plain Markdown — no special syntax

---

## 2. Generate feature specs

Run:

```bash
specleft plan --dry-run
```

SpecLeft parses your PRD and shows what it would create:

```
Planning feature specs...
Dry run: no files will be created.
Features planned: 2
Would create:
  - features/feature-user-authentication.md
  - features/feature-password-reset.md
```

When ready, run without `--dry-run`:

```bash
specleft plan
```

SpecLeft creates one file per feature under `features/`:

```
features/
├── feature-user-authentication.md
└── feature-password-reset.md
```

Each file contains the scenarios extracted from your PRD.

---

## 3. Inspect a feature file

Open `features/feature-user-authentication.md`:

```markdown
# Feature: User Authentication

## Scenarios

### Scenario: Successful login
- Given user has valid credentials
- When user submits login form
- Then user is authenticated and redirected to dashboard

### Scenario: Invalid credentials
- Given user has invalid credentials
- When user submits login form
- Then an error message is displayed
```

This is your **intent specification** — what the system should do, independent of implementation.

---

## 4. Generate skeleton tests

Run:

```bash
specleft test skeleton --dry-run
```

SpecLeft shows the test files it would generate:

```
Will generate: tests/test_feature_user_authentication.py

- Feature: feature-user-authentication
- Scenarios: 2
- Default status: SKIPPED (not implemented)
```

When ready:

```bash
specleft test skeleton
```

The generated test includes the `@specleft` decorator linking it to the spec:

```python
@specleft(
    feature_id="feature-user-authentication",
    scenario_id="successful-login",
    skip=True
)
def test_successful_login():
    with specleft.step("Given user has valid credentials"):
        pass  # TODO: implement

    with specleft.step("When user submits login form"):
        pass  # TODO: implement

    with specleft.step("Then user is authenticated and redirected to dashboard"):
        pass  # TODO: implement
```

---

## 5. Run tests safely

Run pytest:

```bash
pytest
```

Skeleton tests are **skipped**, not failed:

```
SKIPPED: Scenario 'successful-login' not yet implemented
```

**Why this matters:**
- Missing behaviour is visible, not hidden
- CI stays green
- No pressure to implement everything immediately

---

## 6. Implement and track progress

Fill in the test logic and remove `skip=True`:

```python
@specleft(
    feature_id="feature-user-authentication",
    scenario_id="successful-login",
)
def test_successful_login(auth_service):
    with specleft.step("Given user has valid credentials"):
        user = {"username": "alice", "password": "secret123"}

    with specleft.step("When user submits login form"):
        result = auth_service.login(user["username"], user["password"])

    with specleft.step("Then user is authenticated and redirected to dashboard"):
        assert result.authenticated is True
        assert result.redirect_url == "/dashboard"
```

Check implementation status:

```bash
specleft status
```

```
Feature: feature-user-authentication
  ✓ successful-login (implemented)
  ○ invalid-credentials (skipped)

Feature: feature-password-reset
  ○ request-password-reset (skipped)

Coverage: 1/3 scenarios implemented (33%)
```

---

## Optional: Quick demo with `specleft init`

If you don't have a PRD yet, you can see an example feature file:

```bash
specleft init
```

This creates `features/example-feature.md` with a sample structure — useful for understanding the format before writing your own specs.

---

## Next steps

- Add priorities to scenarios (`priority: critical`, `high`, `medium`, `low`)
- Use `specleft next` to find the next scenario to implement
- Set up CI enforcement with `specleft enforce`
- See [AI_AGENTS.md](AI_AGENTS.md) for AI coding agent workflows

---

## For AI Agents

SpecLeft provides machine-verifiable guarantees for autonomous execution:

```bash
specleft contract --format json  # Verify safety guarantees
specleft doctor --format json    # Check installation health
```

All commands support `--format json` for programmatic use.

See [AI_AGENTS.md](AI_AGENTS.md) for complete integration guidance.
