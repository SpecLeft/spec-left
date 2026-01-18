
# SpecLeft SDK

**SpecLeft is a pytest-first SDK for aligning feature specifications with test code — without ceremony, lock-in, or surprises.**

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

## License

MIT
