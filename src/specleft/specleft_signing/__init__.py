# src/specleft_signing/__init__.py
"""SpecLeft Signing - Cryptographic signing and verification for policy files."""

from .canonical import canonical_payload
from .exceptions import (
    InvalidPolicyError,
    InvalidSignatureError,
    SigningKeyError,
    SpecleftSigningError,
    UnknownKeyIdError,
)
from .keys import (
    generate_keypair,
    load_private_key_from_base64,
    load_private_key_from_env,
    load_private_key_from_file,
    load_public_key_from_base64,
    private_key_to_base64,
    public_key_to_base64,
)
from .schema import (
    CoverageRules,
    EvaluationPeriod,
    LicenseInfo,
    PolicyRules,
    PolicyType,
    PriorityRule,
    SignatureBlock,
    SignedPolicy,
    UnsignedPolicy,
)
from .sign import sign_payload_raw, sign_policy
from .verify import (
    TRUSTED_PUBLIC_KEYS,
    VerifyFailure,
    VerifyResult,
    verify_policy,
    verify_signature,
    verify_signature_raw,
)

__version__ = "0.1.0"

__all__ = [
    # Schema
    "PolicyType",
    "EvaluationPeriod",
    "CoverageRules",
    "PriorityRule",
    "PolicyRules",
    "LicenseInfo",
    "SignatureBlock",
    "SignedPolicy",
    "UnsignedPolicy",
    # Canonical
    "canonical_payload",
    # Sign
    "sign_policy",
    "sign_payload_raw",
    # Verify
    "verify_policy",
    "verify_signature",
    "verify_signature_raw",
    "VerifyResult",
    "VerifyFailure",
    "TRUSTED_PUBLIC_KEYS",
    # Keys
    "generate_keypair",
    "private_key_to_base64",
    "public_key_to_base64",
    "load_private_key_from_base64",
    "load_public_key_from_base64",
    "load_private_key_from_file",
    "load_private_key_from_env",
    # Exceptions
    "SpecleftSigningError",
    "InvalidSignatureError",
    "InvalidPolicyError",
    "SigningKeyError",
    "UnknownKeyIdError",
    # Version
    "__version__",
]
