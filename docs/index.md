# SpecLeft Documentation

## Getting Started
- [Installation](installation.md) - Install and verify SpecLeft
- [Quick Start](quick-start.md) - 30-minute hands-on guide
- [Spec Format](spec-format.md) - How to write specifications
- [CLI Reference](cli-reference.md) - All available commands

## For AI Agents 🤖
- **[AI Agents Guide](ai-agents.md)** - Optimized for programmatic adoption
  - Installation verification
  - Common workflows
  - Programmatic API
  - JSON output schemas

## Workflows
- [New Project](workflows/new-project.md) - Starting from scratch
- [Existing Tests](workflows/existing-tests.md) - Adding SpecLeft to existing project
- [TDD Workflow](workflows/tdd-workflow.md) - Spec-first development
- [CI Integration](workflows/ci-integration.md) - GitHub Actions, GitLab CI

## Examples
- [Basic](examples/basic.md) - Simple calculator example
- [Parameterized](examples/parameterized.md) - Using test data tables
- [Complex](examples/complex.md) - Multi-feature project
- [Reverse Engineering](examples/reverse-engineering.md) - Creating specs from tests

## API & Integration
- [Programmatic Usage](api/programmatic.md) - Using SpecLeft from code
- [JSON Schemas](api/json-schemas.md) - Output format reference
```

---

### Phase 5: Real-World Examples & Templates (Week 5)
*Concrete examples agents can copy*

#### 5.1 Add examples/ Directory to Repo
```
examples/
├── basic-calculator/
│   ├── features/
│   │   └── calculator/
│   │       ├── _feature.md
│   │       └── addition/
│   │           ├── _story.md
│   │           └── basic.md
│   ├── tests/
│   │   └── (generated)
│   └── README.md
├── api-testing/
│   ├── features/
│   │   └── auth/
│   │       ├── _feature.md
│   │       ├── login/
│   │       └── register/
│   └── README.md
├── web-app/
│   └── (complex multi-feature example)
└── templates/
    ├── feature-template.md
    ├── story-template.md
    └── scenario-template.md