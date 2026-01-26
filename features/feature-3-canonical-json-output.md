# Feature: Feature 3: Canonical JSON Output
priority: high

## Scenarios

### Scenario: Emit canonical JSON shape
- Given a SpecLeft command is run with `--format json`
- When output is produced
- Then each feature includes:
    - feature_id,
    - title,
    - scnearios with id, priority and status
    - optional metadata fields (nullable)

### Scenario: Scenario IDs are deterministic
- Given a scenario title exists
- When JSON is emitted
- Then the scenario ID is derived consistently from the title
- And repeated runs produce identical IDs
