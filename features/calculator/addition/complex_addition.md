---
scenario_id: complex-addition
priority: high
tags: [math, addition]
execution_time: fast
---

# Scenario: Add 3 numbers

## Test Data
| first | second | third | sum |
| --- | --- | --- | --- |
| 1 | 2 | 3 | 6 |
| 4 | 5 | 6 | 15 |
| 7 | 8 | 9 | 24 |

## Steps
- **Given** a calculator is cleared
- **When** adding {first}, {second}, {third}
- **Then** the result is {sum}
