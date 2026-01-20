"""Shared CLI data types."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from specleft.schema import FeatureSpec, ScenarioSpec, StorySpec


@dataclass(frozen=True)
class TestDiscoveryResult:
    """Result of pytest test discovery."""

    total_tests: int
    specleft_tests: int
    specleft_scenario_ids: frozenset[str]
    error: str | None = None


@dataclass(frozen=True)
class FileSpecleftResult:
    """Result of finding @specleft tests in a file."""

    count: int
    scenario_ids: frozenset[str]


@dataclass(frozen=True)
class ScenarioPlan:
    """Metadata for a planned scenario output."""

    feature_id: str
    feature_name: str
    story_id: str
    story_name: str
    scenario: ScenarioSpec


@dataclass(frozen=True)
class SkeletonPlan:
    """Plan for generating a skeleton test file."""

    feature: FeatureSpec | None
    story: StorySpec | None
    scenarios: list[ScenarioPlan]
    output_path: Path
    content: str
    preview_content: str
    overwrites: bool


@dataclass(frozen=True)
class SkeletonSkipPlan:
    """Plan describing a skipped skeleton output."""

    scenarios: list[ScenarioPlan]
    output_path: Path
    reason: str


@dataclass(frozen=True)
class SkeletonSummary:
    """Summary of skeleton generation steps."""

    feature_count: int
    story_count: int
    scenario_count: int
    output_paths: list[Path]


@dataclass(frozen=True)
class SkeletonPlanResult:
    """Result of skeleton planning."""

    plans: list[SkeletonPlan]
    skipped_plans: list[SkeletonSkipPlan]


@dataclass(frozen=True)
class ScenarioStatus:
    """Status information for a scenario."""

    status: str
    test_file: str | None
    test_function: str | None
    reason: str | None


@dataclass(frozen=True)
class ScenarioStatusEntry:
    """Scenario status entry for reporting."""

    feature: FeatureSpec
    story: StorySpec
    scenario: ScenarioSpec
    status: str
    test_file: str
    test_function: str
    reason: str | None


@dataclass(frozen=True)
class StatusSummary:
    """Coverage summary across scenarios."""

    total_features: int
    total_stories: int
    total_scenarios: int
    implemented: int
    skipped: int
    coverage_percent: int


@dataclass(frozen=True)
class CoverageTally:
    """Coverage tally for a grouping."""

    total: int = 0
    implemented: int = 0


@dataclass(frozen=True)
class CoverageOverall:
    """Overall coverage metrics."""

    total: int
    implemented: int
    skipped: int
    percent: float | None


@dataclass(frozen=True)
class CoverageMetrics:
    """Coverage metrics for multiple groupings."""

    overall: CoverageOverall
    by_feature: dict[str, CoverageTally]
    by_priority: dict[str, CoverageTally]
    by_execution_time: dict[str, CoverageTally]


@dataclass(frozen=True)
class SkeletonScenarioEntry:
    """Flattened scenario entry for skeleton planning."""

    scenario: ScenarioPlan
    output_path: Path
    overwrites: bool
    skip_reason: str | None = None
