---
scenario_id: negative-numbers
priority: medium
tags: [math, addition]
execution_time: fast
---

# Scenario: Add negative numbers

## Test Data
| left | right | expected |
|------|-------|----------|
| -1 | 5 | 4 |
| -2 | -3 | -5 |

## Steps
- **Given** a calculator is cleared
- **When** adding {left} and {right}
- **Then** the result is {expected}
