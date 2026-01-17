---
scenario_id: edge-addition
priority: low
tags: [math, addition, edge-case]
execution_time: fast
---

# Scenario: Add letters

## Test Data
| first | second | third | sum |
| --- | --- | --- | --- |
| a | 2 | c | None |
| 4 | b | 1 | None |
| 7 | 8 | \ | None |

## Steps
- **Given** a calculator is cleared
- **When** adding {first}, {second}, {third}
- **But** things keep moving
- **Then** the result is {sum}
