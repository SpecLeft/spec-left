# src/specleft_signing/canonical.py
"""Deterministic JSON payload generation for signing and verification.

CRITICAL: This module must produce byte-identical output in all contexts.
Any change here will break signature verification for existing policies.
"""

import json
from datetime import date
from typing import Any


def _default_serializer(obj: Any) -> str:
    """JSON serializer for non-standard types."""
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Cannot serialize {type(obj)}")


def canonical_payload(
    policy_type: str, license_data: dict[str, Any], rules: dict[str, Any]
) -> bytes:
    """
    Generate canonical JSON bytes for signing/verification.

    Args:
        policy_type: "core" or "enforce"
        license_data: License info dict (from LicenseInfo.model_dump())
        rules: Rules dict (from PolicyRules.model_dump())

    Returns:
        Deterministic JSON bytes suitable for signing.

    IMPORTANT:
        - Keys are sorted alphabetically at all levels
        - No whitespace (separators=(",", ":"))
        - Dates serialized as ISO format strings
        - Must match EXACTLY between signing and verification
    """
    # Build license block with sorted keys
    license_block: dict[str, Any] = {
        "expires_at": license_data["expires_at"],
        "issued_at": license_data["issued_at"],
        "license_id": license_data["license_id"],
        "licensed_to": license_data["licensed_to"],
    }

    # Add evaluation if present (Enforce only)
    if license_data.get("evaluation"):
        eval_data = license_data["evaluation"]
        license_block["evaluation"] = {
            "ends_at": eval_data["ends_at"],
            "starts_at": eval_data["starts_at"],
        }

    # Add derived_from if present (downgraded Core only)
    if license_data.get("derived_from"):
        license_block["derived_from"] = license_data["derived_from"]

    # Build rules block with sorted keys
    rules_block: dict[str, Any] = {"priorities": {}}

    for priority in sorted(rules.get("priorities", {}).keys()):
        rules_block["priorities"][priority] = {
            "must_be_implemented": rules["priorities"][priority]["must_be_implemented"]
        }

    # Add coverage if present (Enforce only)
    if policy_type == "enforce" and rules.get("coverage"):
        coverage = rules["coverage"]
        rules_block["coverage"] = {
            "fail_below": coverage["fail_below"],
            "threshold_percent": coverage["threshold_percent"],
        }

    # Build final payload
    payload = {
        "license": license_block,
        "policy_type": policy_type,
        "rules": rules_block,
    }

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=_default_serializer,
    ).encode("utf-8")
