# src/specleft_signing/keys.py
"""Key generation, loading, and management utilities."""

import base64
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .exceptions import SigningKeyError


def generate_keypair() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """
    Generate a new Ed25519 keypair.

    Returns:
        Tuple of (private_key, public_key)
    """
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


def private_key_to_base64(private_key: Ed25519PrivateKey) -> str:
    """
    Serialize private key to base64 string.

    Args:
        private_key: Ed25519 private key

    Returns:
        Base64-encoded raw private key bytes (32 bytes)
    """
    raw_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return base64.b64encode(raw_bytes).decode("ascii")


def public_key_to_base64(public_key: Ed25519PublicKey) -> str:
    """
    Serialize public key to base64 string.

    Args:
        public_key: Ed25519 public key

    Returns:
        Base64-encoded raw public key bytes (32 bytes)
    """
    raw_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw_bytes).decode("ascii")


def load_private_key_from_base64(key_b64: str) -> Ed25519PrivateKey:
    """
    Load private key from base64 string.

    Args:
        key_b64: Base64-encoded raw private key bytes

    Returns:
        Ed25519 private key

    Raises:
        SigningKeyError: If key cannot be loaded
    """
    try:
        raw_bytes = base64.b64decode(key_b64)
        return Ed25519PrivateKey.from_private_bytes(raw_bytes)
    except Exception as e:
        raise SigningKeyError(f"Failed to load private key: {e}") from e


def load_public_key_from_base64(key_b64: str) -> Ed25519PublicKey:
    """
    Load public key from base64 string.

    Args:
        key_b64: Base64-encoded raw public key bytes

    Returns:
        Ed25519 public key

    Raises:
        SigningKeyError: If key cannot be loaded
    """
    try:
        raw_bytes = base64.b64decode(key_b64)
        return Ed25519PublicKey.from_public_bytes(raw_bytes)
    except Exception as e:
        raise SigningKeyError(f"Failed to load public key: {e}") from e


def load_private_key_from_file(path: Path) -> Ed25519PrivateKey:
    """
    Load private key from file (base64 content).

    Args:
        path: Path to file containing base64-encoded private key

    Returns:
        Ed25519 private key

    Raises:
        SigningKeyError: If file cannot be read or key cannot be loaded
    """
    try:
        key_b64 = path.read_text().strip()
        return load_private_key_from_base64(key_b64)
    except FileNotFoundError as e:
        raise SigningKeyError(f"Key file not found: {path}") from e
    except SigningKeyError:
        raise
    except Exception as e:
        raise SigningKeyError(f"Failed to load private key from {path}: {e}") from e


def load_private_key_from_env(env_value: str) -> Ed25519PrivateKey:
    """
    Load private key from environment variable value.

    Args:
        env_value: Base64-encoded private key from environment

    Returns:
        Ed25519 private key

    Raises:
        SigningKeyError: If key cannot be loaded
    """
    return load_private_key_from_base64(env_value.strip())
