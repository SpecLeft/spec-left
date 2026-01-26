# src/specleft_signing/sign.py
"""Policy signing operations (requires private key)."""

import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .canonical import canonical_payload
from .schema import (
    SignatureBlock,
    SignedPolicy,
    UnsignedPolicy,
)


def sign_policy(
    policy: UnsignedPolicy,
    private_key: Ed25519PrivateKey,
    key_id: str,
) -> SignedPolicy:
    """
    Sign an unsigned policy.

    Args:
        policy: Policy data to sign
        private_key: Ed25519 private key for signing
        key_id: Identifier for the signing key (e.g., "specleft-prod-2026")

    Returns:
        Complete signed policy with signature block
    """
    # Generate canonical payload
    payload = canonical_payload(
        policy_type=policy.policy_type.value,
        license_data=policy.license.model_dump(),
        rules=policy.rules.model_dump(),
    )

    # Sign the payload
    signature_bytes = private_key.sign(payload)
    signature_b64 = base64.b64encode(signature_bytes).decode("ascii")

    # Build signed policy
    return SignedPolicy(
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        policy_type=policy.policy_type,
        license=policy.license,
        rules=policy.rules,
        signature=SignatureBlock(
            algorithm="ed25519",
            key_id=key_id,
            value=signature_b64,
        ),
    )


def sign_payload_raw(
    payload: bytes,
    private_key: Ed25519PrivateKey,
) -> bytes:
    """
    Sign raw bytes payload.

    Args:
        payload: Bytes to sign (typically from canonical_payload())
        private_key: Ed25519 private key

    Returns:
        Raw signature bytes (64 bytes)
    """
    return private_key.sign(payload)
