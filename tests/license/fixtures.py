"""Test fixtures for license verification tests.

Contains test keypairs and helper functions for creating signed policies.
"""

from __future__ import annotations

import base64
from datetime import date, timedelta
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from specleft.specleft_signing.canonical import canonical_payload
from specleft.specleft_signing.verify import TRUSTED_PUBLIC_KEYS

# Test keypair - ONLY for testing, never use in production
# Generated once and stored here for deterministic tests
_TEST_PRIVATE_KEY_BYTES = bytes.fromhex(
    "4c0d87e7a4a7e8c6f0e9b8a7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7"
)
_TEST_PRIVATE_KEY = Ed25519PrivateKey.from_private_bytes(_TEST_PRIVATE_KEY_BYTES)
_TEST_PUBLIC_KEY: Ed25519PublicKey = _TEST_PRIVATE_KEY.public_key()

# Test key ID used in tests
TEST_KEY_ID = "specleft-test-2026"

# Base64 encoded public key for verification
TEST_PUBLIC_KEY_B64 = base64.b64encode(_TEST_PUBLIC_KEY.public_bytes_raw()).decode(
    "utf-8"
)


def add_trusted_key(key_id: str, public_key_base64: str) -> None:
    """Add a trusted public key for verification.

    This is primarily used for testing with test keypairs.
    Registers the key with specleft_signing's trusted keys.

    Args:
        key_id: Key identifier
        public_key_base64: Base64-encoded Ed25519 public key bytes
    """
    TRUSTED_PUBLIC_KEYS[key_id] = public_key_base64


def remove_trusted_key(key_id: str) -> None:
    """Remove a trusted public key.

    Args:
        key_id: Key identifier to remove
    """
    TRUSTED_PUBLIC_KEYS.pop(key_id, None)


def sign_payload(payload: bytes) -> str:
    """Sign a payload with the test private key.

    Args:
        payload: Bytes to sign

    Returns:
        Base64-encoded signature
    """
    signature = _TEST_PRIVATE_KEY.sign(payload)
    return base64.b64encode(signature).decode("utf-8")


def create_signed_policy_data(
    policy_type: str = "core",
    license_id: str = "lic_test12345678",
    licensed_to: str = "test-owner/test-repo",
    issued_at: date | None = None,
    expires_at: date | None = None,
    evaluation_starts: date | None = None,
    evaluation_ends: date | None = None,
    derived_from: str | None = None,
    priorities: dict[str, dict[str, bool]] | None = None,
    coverage_threshold: int | None = None,
    coverage_fail_below: bool = True,
) -> dict[str, Any]:
    """Create a valid signed policy data structure for testing.

    Args:
        policy_type: "core" or "enforce"
        license_id: License identifier
        licensed_to: Repository pattern
        issued_at: License issue date (default: today)
        expires_at: License expiry date (default: 1 year from now)
        evaluation_starts: Evaluation start (Enforce only)
        evaluation_ends: Evaluation end (Enforce only)
        derived_from: Original license ID if downgraded
        priorities: Priority rules
        coverage_threshold: Coverage threshold percent (Enforce only)
        coverage_fail_below: Whether to fail below threshold

    Returns:
        Dictionary ready to be used as policy data
    """
    today = date.today()
    issued = issued_at or today
    expires = expires_at or (today + timedelta(days=365))

    license_data: dict[str, Any] = {
        "license_id": license_id,
        "licensed_to": licensed_to,
        "issued_at": issued,
        "expires_at": expires,
    }

    if evaluation_starts and evaluation_ends:
        license_data["evaluation"] = {
            "starts_at": evaluation_starts,
            "ends_at": evaluation_ends,
        }

    if derived_from:
        license_data["derived_from"] = derived_from

    rules_data: dict[str, Any] = {
        "priorities": priorities or {"critical": {"must_be_implemented": True}},
    }

    if policy_type == "enforce":
        rules_data["coverage"] = {
            "threshold_percent": coverage_threshold or 100,
            "fail_below": coverage_fail_below,
        }

    # Generate signature
    payload = canonical_payload(policy_type, license_data, rules_data)
    signature = sign_payload(payload)

    return {
        "policy_id": f"{policy_type}-test-v1",
        "policy_version": "1.0",
        "policy_type": policy_type,
        "license": license_data,
        "rules": rules_data,
        "signature": {
            "algorithm": "ed25519",
            "key_id": TEST_KEY_ID,
            "value": signature,
        },
    }


def create_core_policy_data(
    licensed_to: str = "test-owner/test-repo",
    expires_at: date | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a Core policy data structure.

    Args:
        licensed_to: Repository pattern
        expires_at: License expiry date
        **kwargs: Additional arguments passed to create_signed_policy_data

    Returns:
        Dictionary ready to be used as Core policy data
    """
    return create_signed_policy_data(
        policy_type="core",
        licensed_to=licensed_to,
        expires_at=expires_at,
        **kwargs,
    )


def create_enforce_policy_data(
    licensed_to: str = "test-owner/test-repo",
    expires_at: date | None = None,
    coverage_threshold: int = 100,
    evaluation_starts: date | None = None,
    evaluation_ends: date | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create an Enforce policy data structure.

    Args:
        licensed_to: Repository pattern
        expires_at: License expiry date
        coverage_threshold: Required coverage percentage
        evaluation_starts: Evaluation period start
        evaluation_ends: Evaluation period end
        **kwargs: Additional arguments passed to create_signed_policy_data

    Returns:
        Dictionary ready to be used as Enforce policy data
    """
    return create_signed_policy_data(
        policy_type="enforce",
        licensed_to=licensed_to,
        expires_at=expires_at,
        coverage_threshold=coverage_threshold,
        evaluation_starts=evaluation_starts,
        evaluation_ends=evaluation_ends,
        **kwargs,
    )
