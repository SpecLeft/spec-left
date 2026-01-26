"""Policy enforcement engine.

Evaluates policy rules against the current repository state,
checking priority requirements and coverage thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from specleft.specleft_signing.schema import SignedPolicy


@dataclass
class PriorityViolation:
    """A priority rule violation."""

    feature_id: str
    scenario_id: str
    priority: str


@dataclass
class CoverageViolation:
    """A coverage threshold violation."""

    threshold: int
    actual: float


@dataclass
class EnforcementResult:
    """Result of policy enforcement evaluation."""

    failed: bool = False
    ignored_features: list[str] = field(default_factory=list)
    priority_violations: list[PriorityViolation] = field(default_factory=list)
    coverage_violations: list[CoverageViolation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "failed": self.failed,
            "ignored_features": self.ignored_features,
            "priority_violations": [
                {
                    "feature_id": v.feature_id,
                    "scenario_id": v.scenario_id,
                    "priority": v.priority.capitalize(),
                }
                for v in self.priority_violations
            ],
            "coverage_violations": [
                {"threshold": v.threshold, "actual": v.actual}
                for v in self.coverage_violations
            ],
        }


def evaluate_policy(
    policy: SignedPolicy,
    ignored_features: list[str] | None = None,
    features_dir: str = "features",
    tests_dir: str = "tests",
) -> dict[str, Any]:
    """Evaluate policy rules against repository state.

    Checks:
    1. Priority rules: scenarios with must_be_implemented priorities
    2. Coverage rules: overall implementation percentage (Enforce only)

    Args:
        policy: The signed policy to evaluate
        ignored_features: Feature IDs to exclude from evaluation (Enforce only)
        features_dir: Path to features directory
        tests_dir: Path to tests directory

    Returns:
        Dictionary with enforcement results
    """
    from specleft.specleft_signing.schema import PolicyType

    from specleft.commands.status import build_status_entries
    from specleft.commands.types import ScenarioStatusEntry
    from specleft.validator import load_specs_directory

    ignored = set(ignored_features or [])
    result = EnforcementResult(ignored_features=list(ignored))

    # Load specs and build status entries
    try:
        config = load_specs_directory(features_dir)
    except (FileNotFoundError, ValueError):
        # No specs found - nothing to enforce
        return result.to_dict()

    entries = build_status_entries(config, Path(tests_dir))
    # Filter out ignored features
    filtered_entries: list[ScenarioStatusEntry] = []
    for entry in entries:
        if entry.feature.feature_id not in ignored:
            filtered_entries.append(entry)

    # Check priority rules
    for priority_key, rule in policy.rules.priorities.items():
        if rule.must_be_implemented:
            for entry in filtered_entries:
                scenario_priority = (
                    entry.scenario.priority.value if entry.scenario.priority else None
                )
                if scenario_priority == priority_key and entry.status != "implemented":
                    result.priority_violations.append(
                        PriorityViolation(
                            feature_id=entry.feature.feature_id,
                            scenario_id=entry.scenario.scenario_id,
                            priority=priority_key,
                        )
                    )

    # Check coverage rules (Enforce only)
    if policy.policy_type == PolicyType.ENFORCE and policy.rules.coverage:
        coverage_rules = policy.rules.coverage
        total = len(filtered_entries)
        implemented = sum(1 for e in filtered_entries if e.status == "implemented")

        actual_percent = (implemented / total) * 100 if total > 0 else 100.0

        if (
            coverage_rules.fail_below
            and actual_percent < coverage_rules.threshold_percent
        ):
            result.coverage_violations.append(
                CoverageViolation(
                    threshold=coverage_rules.threshold_percent,
                    actual=round(actual_percent, 1),
                )
            )

    # Set failed flag if any violations
    result.failed = bool(result.priority_violations or result.coverage_violations)

    return result.to_dict()
