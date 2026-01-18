
# Getting Started with SpecLeft

This guide walks you through the **30-minute Wow Path** — the fastest way to understand what SpecLeft does, why it exists, and whether it earns a place in your workflow.

By the end of this guide, you should see that SpecLeft:
> - does not break your existing tests
> - makes missing behaviour visible
> - reduces overhead instead of adding it

No prior setup. No commitment. No surprises.

---

## Install and run your existing tests

Install SpecLeft:

```bash
pip install specleft
```

Run your test suite as usual:

```bash
pytest
```

**What happens**
- Tests run exactly as before
- No new failures
- No files created
- No configuration required

SpecLeft is passive by default.

This step exists to prove one thing: **nothing breaks**.

---

## 1. See what SpecLeft can observe

Ask SpecLeft to inspect your repository:

```bash
specleft features stats
```

Example output:

```
Discovered 87 pytest tests
0 linked to feature specs
87 unlinked tests
```

**What this tells you**
- SpecLeft understands your existing tests
- You have not opted into anything yet
- No enforcement, no judgement

At this point, SpecLeft is just observing.

---

## 2. Write a single feature spec

Create one Markdown scenario file and place in `features/auth/login-success.md` directory:

```markdown
---
scenario_id: login-success
priority: high
tags: [auth, smoke]
---

# Scenario: Successful login

## Steps
- Given user has valid credentials
- When user logs in
- Then user is authenticated
```

Notes:
- This is plain Markdown
- No special DSL
- No runtime interpretation

You are describing the scenario's **intent**, not implementation.

---

## 3: Generate a skeleton test (explicit confirmation)

Run:

```bash
specleft test skeleton
```

SpecLeft shows you **exactly** what it plans to generate:

```bash
Will generate: tests/auth/test_login_success.py

- Feature: auth
- Scenario: login-success
- Steps: 3
- Default status: SKIPPED (not implemented)

Preview:

@specleft(feature_id="auth", scenario_id="login-success", skip=True)
def test_login_success():
    with specleft.step("Given user has valid credentials"):
        pass  # TODO - Skeleton test step.

    with specleft.step("When user logs in"):
        pass  # TODO - Skeleton test step.

    with specleft.step("Then user is authenticated"):
        pass  # TODO - Skeleton test step.
```

You are then prompted:

```
Confirm skeleton test creation? [y/N]
```

⚠️ **Nothing is written unless you explicitly confirm.**

---

## 4. Run tests safely

Run pytest again:

```bash
pytest
```

The generated skeleton test is **skipped**, not failed:

```bash
SKIPPED: Scenario 'login-success' defined in spec but not implemented
```

**Why this matters**
- Coverage is visible
- CI stays green
- No pressure to implement immediately

Missing behaviour is explicit, not hidden.

---

## 5. Implement behaviour and see alignment

Fill in the test logic:

```python
@specleft(feature_id="auth", scenario_id="login-success")
def test_login_success(auth_service):
    with specleft.step("Given user has valid credentials"):
        username, password = "admin", "admin123"

    with specleft.step("When user logs in"):
        result = auth_service.login(username, password)

    with specleft.step("Then user is authenticated"):
        assert result is True
```

Run tests:

```bash
pytest
```

Now generate a report:

```bash
specleft test report --open-browser
```

**What you see**
- Scenario listed by name
- Steps in execution order
- Clear pass/fail per step
- Priority and tags visible

---

## 6. Next steps

- Add more scenarios
- Reuse step functions
- Filter tests by feature or priority
- Integrate into CI

#### Full alignment with your tests now awaits.

Any enhancements or bug requests — please raise an [Issue](https://github.com/SpecLeft/spec-left/issues)
