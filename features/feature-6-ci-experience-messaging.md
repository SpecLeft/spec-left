# Feature: Feature 6: CI Experience & Messaging
priority: medium

## Scenarios

### Scenario: CI failure explains intent mismatch
- Given enforcement fails in CI
- When output is printed
- Then the message explains:
    - declared intent,
    - implementation state
    - clear remediation options
- And no marketing or pricing language is included

### Scenario: Documentation and support links on CI failure
priority: high

- Given enforcement fails in CI with {package} policy violation
- When output is printed from `specleft enforce {policy}`
- Then the message includes "Documentation: <link>"
- And the message includes "Support: <link>"
- And both links are actionable and relevant

#### Test Data
| policy | package |
|------|------|
| policy-core.yml | Core+ |
| policy.yml | Enforce |
