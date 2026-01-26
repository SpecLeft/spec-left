# src/specleft_signing/exceptions.py
"""Custom exceptions for specleft-signing."""


class SpecleftSigningError(Exception):
    """Base exception for all signing errors."""

    pass


class InvalidSignatureError(SpecleftSigningError):
    """Raised when signature verification fails."""

    pass


class InvalidPolicyError(SpecleftSigningError):
    """Raised when policy structure is invalid."""

    pass


class SigningKeyError(SpecleftSigningError):
    """Raised when key loading or parsing fails."""

    pass


class UnknownKeyIdError(SpecleftSigningError):
    """Raised when key_id is not in trusted keys."""

    pass
