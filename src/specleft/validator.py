"""Validation helpers for SpecLeft markdown specs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from specleft.schema import SpecsConfig


@dataclass(frozen=True)
class SpecStats:
    """Summary statistics for a specs configuration."""

    feature_count: int
    story_count: int
    scenario_count: int
    step_count: int
    parameterized_scenario_count: int
    tags: set[str]


def load_specs_directory(features_dir: str | Path) -> SpecsConfig:
    """Load and validate specs from a directory."""
    features_path = Path(features_dir)
    if not features_path.exists():
        raise FileNotFoundError(f"Specs directory not found: {features_path}")

    config = SpecsConfig.from_directory(features_path)
    if not config.features:
        raise ValueError(f"No feature specs found in {features_path}")

    _validate_unique_feature_ids(config)
    _validate_unique_story_ids(config)

    return config


def collect_spec_stats(config: SpecsConfig) -> SpecStats:
    """Collect aggregate statistics for a specs configuration."""
    story_count = 0
    scenario_count = 0
    step_count = 0
    parameterized_scenario_count = 0
    tags: set[str] = set()

    for feature in config.features:
        story_count += len(feature.stories)
        tags.update(feature.tags)
        for story in feature.stories:
            tags.update(story.tags)
            for scenario in story.scenarios:
                scenario_count += 1
                step_count += len(scenario.steps)
                if scenario.is_parameterized:
                    parameterized_scenario_count += 1
                tags.update(scenario.tags)

    return SpecStats(
        feature_count=len(config.features),
        story_count=story_count,
        scenario_count=scenario_count,
        step_count=step_count,
        parameterized_scenario_count=parameterized_scenario_count,
        tags=tags,
    )


def _validate_unique_feature_ids(config: SpecsConfig) -> None:
    seen_feature_ids: set[str] = set()
    for feature in config.features:
        if feature.feature_id in seen_feature_ids:
            raise ValueError(f"Duplicate feature_id: {feature.feature_id}")
        seen_feature_ids.add(feature.feature_id)


def _validate_unique_story_ids(config: SpecsConfig) -> None:
    for feature in config.features:
        seen_story_ids: set[str] = set()
        for story in feature.stories:
            if story.story_id in seen_story_ids:
                raise ValueError(
                    f"Duplicate story_id: {story.story_id} in feature {feature.feature_id}"
                )
            seen_story_ids.add(story.story_id)
