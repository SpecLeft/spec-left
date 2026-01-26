# src/specleft_signing/schema.py
"""Pydantic models for SpecLeft policy files."""

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class PolicyType(str, Enum):
    """Policy tier types."""

    CORE = "core"
    ENFORCE = "enforce"


class EvaluationPeriod(BaseModel):
    """Fixed evaluation window (set at purchase time)."""

    starts_at: date
    ends_at: date


class CoverageRules(BaseModel):
    """Coverage enforcement rules (Enforce only)."""

    threshold_percent: int = Field(default=100, ge=0, le=100)
    fail_below: bool = True


class PriorityRule(BaseModel):
    """Rule for a specific priority level."""

    must_be_implemented: bool = False


class PolicyRules(BaseModel):
    """Enforcement rules."""

    priorities: dict[str, PriorityRule] = Field(default_factory=dict)
    coverage: CoverageRules | None = None  # Enforce only


class LicenseInfo(BaseModel):
    """License binding information."""

    license_id: str = Field(pattern=r"^lic_[a-zA-Z0-9]{8,}$")
    licensed_to: str  # "owner/repo" or "owner/*"
    issued_at: date
    expires_at: date
    evaluation: EvaluationPeriod | None = None  # Enforce only
    derived_from: str | None = None  # Downgraded Core only


class SignatureBlock(BaseModel):
    """Cryptographic signature."""

    algorithm: Literal["ed25519"] = "ed25519"
    key_id: str
    value: str  # Base64-encoded signature


class SignedPolicy(BaseModel):
    """Complete signed policy file."""

    policy_id: str
    policy_version: str = Field(pattern=r"^\d+\.\d+$")
    policy_type: PolicyType
    license: LicenseInfo
    rules: PolicyRules
    signature: SignatureBlock

    @model_validator(mode="after")
    def validate_type_rules(self) -> "SignedPolicy":
        """Ensure rules match policy type."""
        if self.policy_type == PolicyType.CORE:
            if self.rules.coverage is not None:
                raise ValueError("Core policies cannot have coverage rules")
            if self.license.evaluation is not None:
                raise ValueError("Core policies cannot have evaluation config")

        if self.policy_type == PolicyType.ENFORCE and self.rules.coverage is None:
            raise ValueError("Enforce policies must have coverage rules")

        return self


class UnsignedPolicy(BaseModel):
    """Policy data before signing (no signature block)."""

    policy_id: str
    policy_version: str = Field(pattern=r"^\d+\.\d+$")
    policy_type: PolicyType
    license: LicenseInfo
    rules: PolicyRules

    @model_validator(mode="after")
    def validate_type_rules(self) -> "UnsignedPolicy":
        """Ensure rules match policy type."""
        if self.policy_type == PolicyType.CORE:
            if self.rules.coverage is not None:
                raise ValueError("Core policies cannot have coverage rules")
            if self.license.evaluation is not None:
                raise ValueError("Core policies cannot have evaluation config")

        if self.policy_type == PolicyType.ENFORCE and self.rules.coverage is None:
            raise ValueError("Enforce policies must have coverage rules")

        return self
