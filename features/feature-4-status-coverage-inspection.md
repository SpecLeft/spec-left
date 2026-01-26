# Feature: Feature 4: Status & Coverage Inspection
priority: high

## Scenarios

### Scenario: Report unimplemented scenarios
priority: high

- Given feature scenarios exist
- And some scenarios are not implemented
- When `specleft status --unimplemented --format json` is executed
- Then unimplemented scenarios are reported clearly

### Scenario: Report implemented scenarios
priority: high

- Given feature scenarios exist
- And some scenarios are implemented
- When `specleft status --implemented --format json` is executed
- Then implemented scenarios are reported clearly

### Scenario: Status of implementation by feature
priority: medium

- Given a scenario title exists
- And test has not been implemented
- When command is run `spec status --feature feature-4-status-coverage-inspection --format json`
- Then feature summary is given for the scenarios and it's status
