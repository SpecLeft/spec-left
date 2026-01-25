"""Shared pytest fixtures for acceptance tests."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from click.testing import CliRunner


@dataclass
class FeatureFiles:
    """Paths to feature-related files created by acceptance test fixtures."""

    feature_path: Path
    test_path: Path
    features_dir: Path
    tests_dir: Path


@dataclass
class FeatureOnlyFiles:
    """Paths to feature-only files (no test files) for contract verification tests."""

    feature_path: Path
    features_dir: Path


@pytest.fixture
def acceptance_workspace() -> Iterator[tuple[CliRunner, Path]]:
    """Provide an isolated workspace with a default features directory."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        workspace = Path.cwd()
        (workspace / "features").mkdir(exist_ok=True)
        yield runner, workspace


# =============================================================================
# Feature 1: Planning Mode - PRD-based fixtures
# Note: Feature 1 tests the `specleft plan` command which generates feature
# files FROM a PRD. These fixtures only write PRD content, not feature files.
# =============================================================================


@dataclass
class PrdFiles:
    """Paths to PRD-related files for planning mode tests."""

    prd_path: Path
    features_dir: Path


# PRD content for test_generate_feature_files_from_prd
_PRD_MULTI_FEATURE = """\
# Product Requirements

## Feature 1: User Authentication
priority: critical

### Scenarios

#### Scenario: User logs in successfully
- Given a registered user
- When they submit valid credentials
- Then they are authenticated

## Feature 2: Payment Processing
priority: high

### Scenarios

#### Scenario: Process credit card payment
- Given a valid credit card
- When payment is submitted
- Then the transaction succeeds
"""

# PRD content for test_derive_feature_filenames_from_prd_headings
_PRD_SLUG_TEST = """\
# Product Requirements Document

## Feature: User Authentication & Login
priority: critical

### Scenarios

#### Scenario: Basic login
- Given a user
- When they log in
- Then they succeed

## Feature: Data Export (CSV/JSON)
priority: high

### Scenarios

#### Scenario: Export data
- Given data exists
- When export is requested
- Then file is created
"""


@pytest.fixture
def feature_1_prd_multi_feature(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, PrdFiles]]:
    """PRD with multiple features for testing feature file generation."""
    runner, workspace = acceptance_workspace

    prd_path = workspace / "prd.md"
    prd_path.write_text(_PRD_MULTI_FEATURE)

    yield (
        runner,
        workspace,
        PrdFiles(
            prd_path=prd_path,
            features_dir=workspace / "features",
        ),
    )


@pytest.fixture
def feature_1_prd_slug_test(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, PrdFiles]]:
    """PRD with special characters in titles for testing slug derivation."""
    runner, workspace = acceptance_workspace

    prd_path = workspace / "prd.md"
    prd_path.write_text(_PRD_SLUG_TEST)

    # Pre-create an existing feature file to test non-overwrite behaviour
    existing_content = "# Feature: User Authentication & Login\n\nCustom content that should NOT be overwritten.\n"
    (workspace / "features" / "feature-user-authentication-login.md").write_text(
        existing_content
    )

    yield (
        runner,
        workspace,
        PrdFiles(
            prd_path=prd_path,
            features_dir=workspace / "features",
        ),
    )


# =============================================================================
# Feature 2: Specification Format
# =============================================================================

_FEATURE_2_MINIMAL = """\
# Feature: Minimal Feature

## Scenarios

### Scenario: Basic scenario
priority: high

- Given a precondition
- When an action occurs
- Then an expected result
"""

_FEATURE_2_WITH_METADATA = """\
---
confidence: high
owner: test-team
component: auth-service
tags:
  - security
  - login
---
# Feature: Feature With Metadata

## Scenarios

### Scenario: Login with metadata
priority: critical

- Given a user with credentials
- When they attempt login
- Then they are authenticated
"""

_FEATURE_2_WITHOUT_METADATA = """\
# Feature: Feature Without Metadata

## Scenarios

### Scenario: Basic operation
priority: medium

- Given a system state
- When an operation occurs
- Then state changes
"""


@pytest.fixture
def feature_2_minimal(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Minimal valid feature file with one scenario."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)

    feature_path = features_dir / "minimal-feature.md"
    feature_path.write_text(_FEATURE_2_MINIMAL)

    test_path = tests_dir / "test_minimal_feature.py"
    test_path.write_text("")  # Empty test file

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=feature_path,
            test_path=test_path,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )


@pytest.fixture
def feature_2_metadata_variants(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles, FeatureFiles]]:
    """Feature files with and without metadata for testing metadata handling."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)

    # Feature WITH metadata
    with_meta_path = features_dir / "feature-with-metadata.md"
    with_meta_path.write_text(_FEATURE_2_WITH_METADATA)
    with_meta_test = tests_dir / "test_feature_with_metadata.py"
    with_meta_test.write_text("")

    # Feature WITHOUT metadata
    without_meta_path = features_dir / "feature-without-metadata.md"
    without_meta_path.write_text(_FEATURE_2_WITHOUT_METADATA)
    without_meta_test = tests_dir / "test_feature_without_metadata.py"
    without_meta_test.write_text("")

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=with_meta_path,
            test_path=with_meta_test,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
        FeatureFiles(
            feature_path=without_meta_path,
            test_path=without_meta_test,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )


# =============================================================================
# Feature 3: Canonical JSON Output
# =============================================================================

_FEATURE_3_USER_AUTH = """\
# Feature: User Authentication
priority: high

## Scenarios

### Scenario: User logs in successfully
priority: critical

- Given a registered user
- When they submit valid credentials
- Then they are authenticated

### Scenario: User logout
priority: medium

- Given an authenticated user
- When they click logout
- Then the session is terminated
"""

_TEST_3_USER_AUTH = """\
from specleft import specleft

@specleft(feature_id="feature-user-authentication", scenario_id="user-logs-in-successfully")
def test_user_logs_in_successfully():
    pass
"""

_FEATURE_3_SLUGIFICATION = """\
# Feature: Slugification Test
priority: high

## Scenarios

### Scenario: User Logs In Successfully
priority: high

- Given a user
- When they log in
- Then success

### Scenario: Handle Edge-Case (Special Characters!)
priority: medium

- Given edge case
- When handled
- Then pass

### Scenario: Multi   Word   Spaces
priority: low

- Given words
- When spaced
- Then normalized
"""


@pytest.fixture
def feature_3_canonical_json(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature with scenarios for testing canonical JSON output shape."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)

    feature_path = features_dir / "feature-user-authentication.md"
    feature_path.write_text(_FEATURE_3_USER_AUTH)

    test_path = tests_dir / "test_feature_user_authentication.py"
    test_path.write_text(_TEST_3_USER_AUTH)

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=feature_path,
            test_path=test_path,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )


@pytest.fixture
def feature_3_slugification(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature with varied title formats for testing ID slugification."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)

    feature_path = features_dir / "feature-slugification-test.md"
    feature_path.write_text(_FEATURE_3_SLUGIFICATION)

    test_path = tests_dir / "test_feature_slugification_test.py"
    test_path.write_text("")

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=feature_path,
            test_path=test_path,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )


# =============================================================================
# Feature 4: Status & Coverage Inspection
# =============================================================================

_FEATURE_4_USER_AUTH = """\
# Feature: User Authentication
priority: high

## Scenarios

### Scenario: User logs in successfully
priority: critical

- Given a registered user
- When they submit valid credentials
- Then they are authenticated

### Scenario: User password reset
priority: high

- Given a user forgot password
- When they request reset
- Then email is sent

### Scenario: User logout
priority: medium

- Given an authenticated user
- When they click logout
- Then session is terminated
"""

_TEST_4_USER_AUTH_PARTIAL = '''\
from specleft import specleft

@specleft(feature_id="feature-user-authentication", scenario_id="user-logs-in-successfully")
def test_user_logs_in_successfully():
    """This test IS implemented (no skip=True)."""
    pass
'''

_FEATURE_4_PAYMENT = """\
# Feature: Payment Processing
priority: high

## Scenarios

### Scenario: Process credit card payment
priority: critical

- Given a valid credit card
- When payment is submitted
- Then transaction succeeds

### Scenario: Process refund
priority: high

- Given a completed transaction
- When refund is requested
- Then amount is returned

### Scenario: Payment history
priority: low

- Given a user account
- When viewing history
- Then transactions are listed
"""

_TEST_4_PAYMENT_PARTIAL = '''\
from specleft import specleft

@specleft(feature_id="feature-payment-processing", scenario_id="process-credit-card-payment")
def test_process_credit_card_payment():
    """Implemented test."""
    pass

@specleft(feature_id="feature-payment-processing", scenario_id="process-refund")
def test_process_refund():
    """Implemented test."""
    pass

# Note: payment-history is NOT implemented
'''

_FEATURE_4_AUTH_FILTER = """\
# Feature: User Authentication
priority: high

## Scenarios

### Scenario: User login
priority: critical

- Given a user
- When they log in
- Then success

### Scenario: User signup
priority: high

- Given a new user
- When they sign up
- Then account created
"""

_FEATURE_4_BILLING = """\
# Feature: Billing System
priority: high

## Scenarios

### Scenario: Generate invoice
priority: critical

- Given a completed order
- When billing runs
- Then invoice is generated

### Scenario: Apply discount
priority: medium

- Given a coupon code
- When applied
- Then price is reduced
"""

_TEST_4_AUTH_ONLY = """\
from specleft import specleft

@specleft(feature_id="feature-auth", scenario_id="user-login")
def test_user_login():
    pass
"""


@pytest.fixture
def feature_4_unimplemented(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature with partial implementation for testing --unimplemented filter."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)

    feature_path = features_dir / "feature-user-authentication.md"
    feature_path.write_text(_FEATURE_4_USER_AUTH)

    test_path = tests_dir / "test_feature_user_authentication.py"
    test_path.write_text(_TEST_4_USER_AUTH_PARTIAL)

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=feature_path,
            test_path=test_path,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )


@pytest.fixture
def feature_4_implemented(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature with partial implementation for testing --implemented filter."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)

    feature_path = features_dir / "feature-payment-processing.md"
    feature_path.write_text(_FEATURE_4_PAYMENT)

    test_path = tests_dir / "test_feature_payment_processing.py"
    test_path.write_text(_TEST_4_PAYMENT_PARTIAL)

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=feature_path,
            test_path=test_path,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )


@pytest.fixture
def feature_4_multi_feature_filter(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles, FeatureFiles]]:
    """Multiple features for testing --feature filter."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)

    # Auth feature
    auth_path = features_dir / "feature-auth.md"
    auth_path.write_text(_FEATURE_4_AUTH_FILTER)
    auth_test = tests_dir / "test_feature_auth.py"
    auth_test.write_text(_TEST_4_AUTH_ONLY)

    # Billing feature (no tests)
    billing_path = features_dir / "feature-billing.md"
    billing_path.write_text(_FEATURE_4_BILLING)
    billing_test = tests_dir / "test_feature_billing.py"
    billing_test.write_text("")

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=auth_path,
            test_path=auth_test,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
        FeatureFiles(
            feature_path=billing_path,
            test_path=billing_test,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )


# =============================================================================
# Feature 5: Policy Enforcement
# =============================================================================

_FEATURE_5_USER_AUTH = """\
# Feature: User Authentication
priority: high

## Scenarios

### Scenario: User login critical
priority: critical

- Given a registered user
- When they submit valid credentials
- Then they are authenticated

### Scenario: User password reset
priority: high

- Given a user forgot password
- When they request reset
- Then email is sent

### Scenario: User logout
priority: medium

- Given an authenticated user
- When they click logout
- Then session is terminated
"""

_TEST_5_MEDIUM_ONLY = '''\
from specleft import specleft

@specleft(feature_id="feature-user-authentication", scenario_id="user-logout")
def test_user_logout():
    """Only medium priority implemented."""
    pass
'''

_FEATURE_5_PAYMENT = """\
# Feature: Payment Processing
priority: high

## Scenarios

### Scenario: Process payment
priority: critical

- Given a valid payment method
- When payment is submitted
- Then transaction succeeds

### Scenario: Refund payment
priority: high

- Given a completed transaction
- When refund is requested
- Then amount is returned

### Scenario: View payment history
priority: low

- Given a user account
- When viewing history
- Then transactions are listed
"""

_TEST_5_PAYMENT_FULL = '''\
from specleft import specleft

@specleft(feature_id="feature-payment-processing", scenario_id="process-payment")
def test_process_payment():
    """Critical scenario implemented."""
    pass

@specleft(feature_id="feature-payment-processing", scenario_id="refund-payment")
def test_refund_payment():
    """High priority scenario implemented."""
    pass

# Note: view-payment-history (low priority) intentionally not implemented
'''

_FEATURE_5_USER_MGMT = """\
# Feature: User Management
priority: high

## Scenarios

### Scenario: Create user
priority: critical

- Given an admin
- When creating a user
- Then user is created
"""


@pytest.fixture
def feature_5_policy_violation(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature with unimplemented critical/high scenarios for policy violation test."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")

    feature_path = features_dir / "feature-user-authentication.md"
    feature_path.write_text(_FEATURE_5_USER_AUTH)

    test_path = tests_dir / "test_auth.py"
    test_path.write_text(_TEST_5_MEDIUM_ONLY)

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=feature_path,
            test_path=test_path,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )


@pytest.fixture
def feature_5_policy_satisfied(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature with all critical/high scenarios implemented for passing enforcement."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)

    feature_path = features_dir / "feature-payment-processing.md"
    feature_path.write_text(_FEATURE_5_PAYMENT)

    test_path = tests_dir / "test_payment.py"
    test_path.write_text(_TEST_5_PAYMENT_FULL)

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=feature_path,
            test_path=test_path,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )


@pytest.fixture
def feature_5_invalid_signature(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature for testing invalid policy signature rejection."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)

    feature_path = features_dir / "feature-user-management.md"
    feature_path.write_text(_FEATURE_5_USER_MGMT)

    test_path = tests_dir / "test_user_management.py"
    test_path.write_text("")

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=feature_path,
            test_path=test_path,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )


# =============================================================================
# Feature 6: CI Experience & Messaging
# =============================================================================

_FEATURE_6_ORDER = """\
# Feature: Order Processing
priority: high

## Scenarios

### Scenario: Process critical order
priority: critical

- Given a pending order
- When processing is triggered
- Then order is fulfilled

### Scenario: Archive old orders
priority: low

- Given orders older than 90 days
- When archival runs
- Then orders are archived
"""

_TEST_6_ORDER_LOW_ONLY = '''\
from specleft import specleft

@specleft(feature_id="feature-order-processing", scenario_id="archive-old-orders")
def test_archive_old_orders():
    """Only low priority implemented - critical is missing."""
    pass
'''

_FEATURE_6_NOTIFICATION = """\
# Feature: Notification Service
priority: high

## Scenarios

### Scenario: Send critical alert
priority: critical

- Given a critical event
- When alert is triggered
- Then notification is sent

### Scenario: Log notification history
priority: medium

- Given notifications sent
- When history is queried
- Then records are returned
"""

_TEST_6_NOTIFICATION_MEDIUM_ONLY = '''\
from specleft import specleft

@specleft(feature_id="feature-notification-service", scenario_id="log-notification-history")
def test_log_notification_history():
    """Only medium priority implemented."""
    pass
'''


@pytest.fixture
def feature_6_ci_failure(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature with unimplemented critical scenario for CI failure messaging test."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")

    feature_path = features_dir / "feature-order-processing.md"
    feature_path.write_text(_FEATURE_6_ORDER)

    test_path = tests_dir / "test_orders.py"
    test_path.write_text(_TEST_6_ORDER_LOW_ONLY)

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=feature_path,
            test_path=test_path,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )


@pytest.fixture
def feature_6_doc_links(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature for testing documentation/support link presence on CI failure."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")

    feature_path = features_dir / "feature-notification-service.md"
    feature_path.write_text(_FEATURE_6_NOTIFICATION)

    test_path = tests_dir / "test_notifications.py"
    test_path.write_text(_TEST_6_NOTIFICATION_MEDIUM_ONLY)

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=feature_path,
            test_path=test_path,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )


# =============================================================================
# Feature 7: Autonomous Agent Test Execution
# =============================================================================

_FEATURE_7_API_GATEWAY = """\
# Feature: API Gateway
priority: high

## Scenarios

### Scenario: Authenticate request
priority: critical

- Given an incoming API request
- When authentication is checked
- Then valid tokens are accepted

### Scenario: Rate limit exceeded
priority: high

- Given a client exceeding rate limits
- When request is received
- Then 429 response is returned

### Scenario: Log request metrics
priority: low

- Given any API request
- When processing completes
- Then metrics are logged
"""

_TEST_7_API_GATEWAY_LOW_ONLY = '''\
from specleft import specleft

@specleft(feature_id="feature-api-gateway", scenario_id="log-request-metrics")
def test_log_request_metrics():
    """Only low priority implemented - critical and high remain."""
    pass
'''

_FEATURE_7_DATA_EXPORT = """\
# Feature: Data Export
priority: high

## Scenarios

### Scenario: Export to CSV
priority: critical

- Given data records exist
- When CSV export is requested
- Then a valid CSV file is generated

### Scenario: Export to JSON
priority: high

- Given data records exist
- When JSON export is requested
- Then a valid JSON file is generated
"""

_FEATURE_7_CACHE_SERVICE = """\
# Feature: Cache Service
priority: high

## Scenarios

### Scenario: Cache hit returns data
priority: critical

- Given data exists in cache
- When cache lookup is performed
- Then cached data is returned

### Scenario: Cache miss triggers fetch
priority: high

- Given data not in cache
- When cache lookup is performed
- Then data is fetched from source
"""

_TEST_7_CACHE_IMPLEMENTED = '''\
from specleft import specleft

@specleft(
    feature_id="feature-cache-service",
    scenario_id="cache-hit-returns-data",
)
def test_cache_hit_returns_data():
    """Cache hit returns data - IMPLEMENTED by agent."""
    with specleft.step("Given data exists in cache"):
        cache = {"key": "value"}

    with specleft.step("When cache lookup is performed"):
        result = cache.get("key")

    with specleft.step("Then cached data is returned"):
        assert result == "value"
'''

_FEATURE_7_USER_SERVICE = """\
# Feature: User Service
priority: high

## Scenarios

### Scenario: Create user
priority: critical

- Given valid user data
- When create user is called
- Then user is created

### Scenario: Update user
priority: high

- Given existing user
- When update is called
- Then user is updated

### Scenario: Delete user
priority: medium

- Given existing user
- When delete is called
- Then user is removed
"""

_TEST_7_USER_SERVICE_PARTIAL = '''\
from specleft import specleft

@specleft(
    feature_id="feature-user-service",
    scenario_id="create-user",
)
def test_create_user():
    """Create user - IMPLEMENTED."""
    with specleft.step("Given valid user data"):
        user_data = {"name": "test"}

    with specleft.step("When create user is called"):
        result = {"id": 1, **user_data}

    with specleft.step("Then user is created"):
        assert result["id"] == 1

@specleft(
    feature_id="feature-user-service",
    scenario_id="update-user",
    skip=True,
    reason="Not yet implemented",
)
def test_update_user():
    """Update user - SKIPPED."""
    pass

# Note: delete-user has no test at all (also unimplemented)
'''


@pytest.fixture
def feature_7_next_scenario(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature with unimplemented scenarios for testing `specleft next`."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")

    feature_path = features_dir / "feature-api-gateway.md"
    feature_path.write_text(_FEATURE_7_API_GATEWAY)

    test_path = tests_dir / "test_api_gateway.py"
    test_path.write_text(_TEST_7_API_GATEWAY_LOW_ONLY)

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=feature_path,
            test_path=test_path,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )


@pytest.fixture
def feature_7_skeleton(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature for testing `specleft test skeleton` generation."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")

    # Create tmp output directory for skeleton generation
    (workspace / "tmp").mkdir(exist_ok=True)

    feature_path = features_dir / "feature-data-export.md"
    feature_path.write_text(_FEATURE_7_DATA_EXPORT)

    test_path = tests_dir / "test_feature_data_export.py"
    test_path.write_text("")

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=feature_path,
            test_path=test_path,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )


@pytest.fixture
def feature_7_agent_implements(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature with implemented test for testing status reflection."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")

    feature_path = features_dir / "feature-cache-service.md"
    feature_path.write_text(_FEATURE_7_CACHE_SERVICE)

    test_path = tests_dir / "test_cache_service.py"
    test_path.write_text(_TEST_7_CACHE_IMPLEMENTED)

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=feature_path,
            test_path=test_path,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )


@pytest.fixture
def feature_7_coverage(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature with partial implementation for testing coverage reporting."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")

    feature_path = features_dir / "feature-user-service.md"
    feature_path.write_text(_FEATURE_7_USER_SERVICE)

    test_path = tests_dir / "test_user_service.py"
    test_path.write_text(_TEST_7_USER_SERVICE_PARTIAL)

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=feature_path,
            test_path=test_path,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )


# =============================================================================
# Feature 8: Agent Contract Introspection
# =============================================================================

_FEATURE_8_TEST = """\
# Feature: Test Feature
priority: medium

## Scenarios

### Scenario: Basic test
- Given a precondition
- When an action occurs
- Then expected result
"""

_FEATURE_8_AUTH = """\
# Feature: Auth
priority: high

## Scenarios

### Scenario: User login
- Given valid credentials
- When login is attempted
- Then user is authenticated
"""


@pytest.fixture
def feature_8_contract(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Minimal feature for testing `specleft contract` output."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)

    feature_path = features_dir / "feature-test.md"
    feature_path.write_text(_FEATURE_8_TEST)

    test_path = tests_dir / "test_feature_test.py"
    test_path.write_text("")

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=feature_path,
            test_path=test_path,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )


@pytest.fixture
def feature_8_contract_minimal(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureOnlyFiles]]:
    """Minimal feature for testing `specleft contract test` side-effect behavior.

    Only creates a feature file, no tests directory. Used by tests that verify
    `contract test` does not create files as side effects.
    """
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    feature_path = features_dir / "feature-test.md"
    feature_path.write_text(_FEATURE_8_TEST)

    yield (
        runner,
        workspace,
        FeatureOnlyFiles(
            feature_path=feature_path,
            features_dir=features_dir,
        ),
    )


@pytest.fixture
def feature_8_contract_test(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature for testing `specleft contract test` compliance."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")

    feature_path = features_dir / "feature-auth.md"
    feature_path.write_text(_FEATURE_8_AUTH)

    test_path = tests_dir / "test_feature_auth.py"
    test_path.write_text("")

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=feature_path,
            test_path=test_path,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )
