---
# Scenario-level metadata
scenario_id: [SCENARIO_ID]
story_id: [STORY_ID] # Links to parent story
feature_id: [FEATURE_ID]
priority: [PRIORITY]
tags: [[TAG_1], [TAG_2]]
owner: [OWNER]
test_type: [TEST_TYPE]
execution_time: [EXECUTION_TIME]
dependencies: [[DEPENDENCY_1], [DEPENDENCY_2]]

# Optional external references
external_refs:
	- type: [REF_TYPE]
		id: [REF_ID]
		url: [REF_URL]
	- type: [REF_TYPE]
		id: [REF_ID]
		url: [REF_URL]
---

# Scenario: [SCENARIO_NAME]

## Description
[SCENARIO_DESCRIPTION]

## Test Data
| username | password | description           |
|----------|----------|-----------------------|
| admin    | admin123 | Admin user account    |
| user     | password | Standard user account |

## Steps
- **Given** user has valid credentials
- **When** user enters username `{username}` and password `{password}`
- **And** user clicks login button
- **Then** user is authenticated
- **And** session token is returned
- **And** user is redirected to dashboard

## Notes
- Session token expires after 24 hours
- Failed login attempts are logged for security audit
