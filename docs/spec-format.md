# SpecLeft Specification Format

SpecLeft uses Markdown files with YAML frontmatter to describe features, stories, and scenarios. The directory structure mirrors the hierarchy:

```
features/
├── <feature>/
│   ├── _feature.md
│   └── <story>/
│       ├── _story.md
│       └── <scenario>.md
```

## Feature File (`_feature.md`)

```markdown
---
feature_id: calculator
component: math
owner: core-team
priority: high
tags: [math, core]
---

# Feature: Calculator

Basic arithmetic operations for the calculator module.
```

## Story File (`_story.md`)

```markdown
---
story_id: addition
priority: high
tags: [math, addition]
---

# Story: Addition

Adding numbers with the calculator.
```

## Scenario File (`<scenario>.md`)

```markdown
---
scenario_id: basic-addition
priority: high
tags: [math, addition]
execution_time: fast
---

# Scenario: Add two numbers

## Steps
- **Given** a calculator is cleared
- **When** adding 2 and 3
- **Then** the result is 5
```

### Test Data Tables

Add `## Test Data` for parameterized scenarios:

```markdown
## Test Data
| left | right | expected |
|------|-------|----------|
| -1 | 5 | 4 |
| -2 | -3 | -5 |

## Steps
- **Given** a calculator is cleared
- **When** adding {left} and {right}
- **Then** the result is {expected}
```

## Valid Values

- Step types: `Given`, `When`, `Then`, `And`, `But`
- Priority: `critical`, `high`, `medium`, `low`
- Execution time: `fast`, `medium`, `slow`

Scenario IDs must be unique across the entire specs directory and match `^[a-z0-9-]+$`.
Feature and story IDs use the same pattern.
