"""
Example tests demonstrating SpecLeft SDK features.

This file shows how to use:
- @specleft decorator for test metadata
- specleft.step() context manager for step tracking
- @shared_step decorator for shared step methods
- Parameterized tests with test_data from specs
"""

import re

import pytest
from specleft import shared_step, specleft

# =============================================================================
# Helper functions (simulating application code)
# =============================================================================


def extract_unit(measurement: str) -> str | None:
    """Extract the unit suffix from a measurement string.

    Args:
        measurement: A string like "10kg", "5lb", "100g"

    Returns:
        The unit suffix (e.g., "kg", "lb", "g") or None if no unit found.
    """
    match = re.search(r"[a-zA-Z]+$", measurement)
    return match.group() if match else None


class AuthService:
    """Simple authentication service for demonstration."""

    def __init__(self) -> None:
        self.sessions: dict[str, bool] = {}
        self.valid_users = {
            "admin": "admin123",
            "user": "password",
        }

    def login(self, username: str, password: str) -> bool:
        """Attempt to log in a user.

        Returns:
            True if login successful, False otherwise.
        """
        if self.valid_users.get(username) == password:
            self.sessions[username] = True
            return True
        return False

    def is_authenticated(self, username: str) -> bool:
        """Check if a user has an active session."""
        return self.sessions.get(username, False)

    def has_session(self, username: str) -> bool:
        """Check if a session exists for the user."""
        return username in self.sessions


# =============================================================================
# Reusable Step Methods
# These functions are automatically traced when called from @specleft tests
# =============================================================================


@shared_step("User logs in with username '{username}'")
def login_user(auth_service: AuthService, username: str, password: str) -> bool:
    """Reusable step method for logging in a user.

    When called from within a @specleft decorated test, this function's
    execution is automatically traced with parameter interpolation.

    Args:
        auth_service: The authentication service instance
        username: The username to log in with
        password: The password to use

    Returns:
        True if login successful, False otherwise
    """
    return auth_service.login(username, password)


@shared_step("Verify user '{username}' is authenticated")
def verify_authenticated(auth_service: AuthService, username: str) -> None:
    """Reusable step to verify a user is authenticated.

    Args:
        auth_service: The authentication service instance
        username: The username to verify

    Raises:
        AssertionError: If user is not authenticated
    """
    assert auth_service.is_authenticated(
        username
    ), f"User '{username}' is not authenticated"


@shared_step("Verify session exists for '{username}'")
def verify_session_exists(auth_service: AuthService, username: str) -> None:
    """Reusable step to verify a session exists.

    Args:
        auth_service: The authentication service instance
        username: The username to check

    Raises:
        AssertionError: If session does not exist
    """
    assert auth_service.has_session(username), f"No session found for '{username}'"


# =============================================================================
# Pytest Fixtures
# =============================================================================


@pytest.fixture
def auth_service() -> AuthService:
    """Provide a fresh AuthService instance for each test."""
    return AuthService()


# =============================================================================
# Feature: auth - User Authentication
# =============================================================================


@specleft(feature_id="auth", scenario_id="login-success")
@pytest.mark.parametrize(
    "username, password",
    [
        ("admin", "admin123"),
        ("user", "password"),
    ],
    ids=["Admin user account", "Standard user account"],
)
def test_login_success(auth_service: AuthService, username: str, password: str) -> None:
    """Successful login with valid credentials.

    This test demonstrates:
    - Parameterized tests with @pytest.mark.parametrize
    - Using @shared_step decorated functions for automatic step tracing
    - Parameter interpolation in step descriptions

    Priority: critical
    Tags: smoke, authentication, critical
    """
    with specleft.step("Given user has valid credentials"):
        assert username in auth_service.valid_users
        assert auth_service.valid_users[username] == password

    # Using shared step - automatically traced with parameter values
    result = login_user(auth_service, username, password)

    with specleft.step("Then user is authenticated and session is created"):
        assert result is True

    # More shared steps for verification
    verify_authenticated(auth_service, username)
    verify_session_exists(auth_service, username)


@specleft(feature_id="auth", scenario_id="login-invalid-credentials")
def test_login_invalid_credentials(auth_service: AuthService) -> None:
    """Login fails with invalid credentials.

    This test demonstrates error handling scenarios with step tracking.

    Priority: high
    Tags: authentication, negative, security
    """
    username = "admin"
    wrong_password = "wrong_password"

    with specleft.step("Given user has invalid credentials"):
        assert username in auth_service.valid_users
        assert auth_service.valid_users[username] != wrong_password

    with specleft.step("When user attempts to login"):
        result = auth_service.login(username, wrong_password)

    with specleft.step("Then login fails with error message"):
        assert result is False
        assert not auth_service.is_authenticated(username)


# =============================================================================
# Feature: parse - Unit Parsing
# =============================================================================


@specleft(feature_id="parse", scenario_id="extract-unit-valid")
@pytest.mark.parametrize(
    "input_str, expected",
    [
        ("10kg", "kg"),
        ("5lb", "lb"),
        ("100g", "g"),
    ],
    ids=["Kilograms", "Pounds", "Grams"],
)
def test_extract_unit_valid(input_str: str, expected: str) -> None:
    """Extract unit from valid input.

    This test demonstrates parameterized tests for data-driven testing.

    Priority: critical
    Tags: smoke, parsing
    """
    with specleft.step(f"When extracting unit from '{input_str}'"):
        result = extract_unit(input_str)

    with specleft.step(f"Then unit should be '{expected}'"):
        assert result == expected, f"Expected '{expected}', got '{result}'"


@specleft(feature_id="parse", scenario_id="extract-unit-invalid")
def test_extract_unit_invalid() -> None:
    """Handle invalid input gracefully.

    This test demonstrates proper handling of edge cases.

    Priority: high
    Tags: parsing, error-handling
    """
    with specleft.step("Given input string has no unit"):
        input_str = "12345"

    with specleft.step("When attempting to extract unit"):
        result = extract_unit(input_str)

    with specleft.step("Then should return None"):
        assert result is None, f"Expected None, got '{result}'"
