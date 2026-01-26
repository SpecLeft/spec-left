# src/specleft_signing/verify.py
"""Policy signature verification (public key only)."""

import base64
from dataclasses import dataclass
from datetime import date
from enum import Enum

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .canonical import canonical_payload
from .exceptions import InvalidSignatureError, UnknownKeyIdError
from .keys import load_public_key_from_base64
from .schema import SignedPolicy

# =============================================================================
# TRUSTED PUBLIC KEYS
# =============================================================================
TRUSTED_PUBLIC_KEYS: dict[str, str] = {
    "specleft-dev-2026": "OBN/ZLH6RUg3KWLCW37U3iGnXQVULJLB0sDF/MGw/v0="
}


class VerifyFailure(Enum):
    """Verification failure reasons."""

    INVALID_SIGNATURE = "invalid_signature"
    UNKNOWN_KEY_ID = "unknown_key_id"
    EXPIRED = "expired"
    EVALUATION_EXPIRED = "evaluation_expired"


@dataclass
class VerifyResult:
    """Result of policy verification."""

    valid: bool
    failure: VerifyFailure | None = None
    message: str | None = None


def get_trusted_public_key(key_id: str) -> Ed25519PublicKey:
    """
    Get a trusted public key by ID.

    Args:
        key_id: Key identifier

    Returns:
        Ed25519 public key

    Raises:
        UnknownKeyIdError: If key_id is not in trusted keys
    """
    if key_id not in TRUSTED_PUBLIC_KEYS:
        raise UnknownKeyIdError(f"Unknown key_id: {key_id}")

    return load_public_key_from_base64(TRUSTED_PUBLIC_KEYS[key_id])


def verify_signature(policy: SignedPolicy) -> bool:
    """
    Verify policy signature only (no expiry or date checks).

    Args:
        policy: Signed policy to verify

    Returns:
        True if signature is valid

    Raises:
        UnknownKeyIdError: If key_id is not trusted
        InvalidSignatureError: If signature verification fails
    """
    # Get public key
    public_key = get_trusted_public_key(policy.signature.key_id)

    # Reconstruct canonical payload
    payload = canonical_payload(
        policy_type=policy.policy_type.value,
        license_data=policy.license.model_dump(),
        rules=policy.rules.model_dump(),
    )

    # Decode signature
    try:
        signature = base64.b64decode(policy.signature.value)
    except Exception as e:
        raise InvalidSignatureError(f"Invalid signature encoding: {e}") from e

    # Verify
    try:
        public_key.verify(signature, payload)
        return True
    except InvalidSignature as e:
        raise InvalidSignatureError("Signature verification failed") from e


def verify_policy(policy: SignedPolicy, check_dates: bool = True) -> VerifyResult:
    """
    Full policy verification including signature, expiry, and evaluation.

    Args:
        policy: Signed policy to verify
        check_dates: If True, verify expiration and evaluation dates

    Returns:
        VerifyResult with valid=True or valid=False with failure details

    Note:
        This does NOT check repository binding. That must be done by the
        caller (SpecLeft CLI) which has access to the current repository.
    """
    # 1. Check key_id is known
    if policy.signature.key_id not in TRUSTED_PUBLIC_KEYS:
        return VerifyResult(
            valid=False,
            failure=VerifyFailure.UNKNOWN_KEY_ID,
            message=f"Unknown signing key: {policy.signature.key_id}",
        )

    # 2. Verify signature
    try:
        verify_signature(policy)
    except InvalidSignatureError as e:
        return VerifyResult(
            valid=False,
            failure=VerifyFailure.INVALID_SIGNATURE,
            message=str(e),
        )
    except UnknownKeyIdError as e:
        return VerifyResult(
            valid=False,
            failure=VerifyFailure.UNKNOWN_KEY_ID,
            message=str(e),
        )

    if not check_dates:
        return VerifyResult(valid=True)

    # 3. Check license expiration
    today = date.today()
    if policy.license.expires_at < today:
        return VerifyResult(
            valid=False,
            failure=VerifyFailure.EXPIRED,
            message=f"License expired on {policy.license.expires_at}",
        )

    # 4. Check evaluation period (Enforce only)
    if policy.license.evaluation and today > policy.license.evaluation.ends_at:
        return VerifyResult(
            valid=False,
            failure=VerifyFailure.EVALUATION_EXPIRED,
            message=f"Evaluation period ended on {policy.license.evaluation.ends_at}",
        )

    return VerifyResult(valid=True)


def verify_signature_raw(
    payload: bytes,
    signature: bytes,
    public_key: Ed25519PublicKey,
) -> bool:
    """
    Verify raw signature bytes against payload.

    Args:
        payload: Original signed payload
        signature: Signature bytes to verify
        public_key: Ed25519 public key

    Returns:
        True if valid, False otherwise
    """
    try:
        public_key.verify(signature, payload)
        return True
    except InvalidSignature:
        return False
