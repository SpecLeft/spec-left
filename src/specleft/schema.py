"""SpecLeft Schema Definitions.

Pydantic models for parsing and validating Markdown specifications.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class StepType(str, Enum):
    """Valid step types for BDD-style specifications."""

    GIVEN = "given"
    WHEN = "when"
    THEN = "then"
    AND = "and"
    BUT = "but"


class Priority(str, Enum):
    """Priority levels for features, stories, and scenarios."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExecutionTime(str, Enum):
    """Expected execution time classification."""

    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"


class SpecStep(BaseModel):
    """Individual test step (Given/When/Then)."""

    type: StepType
    description: str = Field(min_length=1)
    data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        return value.strip()


class SpecDataRow(BaseModel):
    """Single row of test data for parameterization."""

    params: dict[str, Any]
    description: str | None = None

    @field_validator("params")
    @classmethod
    def validate_params_not_empty(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("Test data params cannot be empty")
        return value


class ScenarioSpec(BaseModel):
    """Scenario specification parsed from a Markdown file."""

    scenario_id: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str
    description: str | None = None
    priority: Priority = Priority.MEDIUM
    tags: list[str] = Field(default_factory=list)
    execution_time: ExecutionTime = ExecutionTime.FAST
    steps: list[SpecStep] = Field(default_factory=list)
    test_data: list[SpecDataRow] = Field(default_factory=list)
    source_file: Path | None = None

    @property
    def is_parameterized(self) -> bool:
        return len(self.test_data) > 0

    @property
    def test_function_name(self) -> str:
        return f"test_{self.scenario_id.replace('-', '_')}"


class StorySpec(BaseModel):
    """Story specification parsed from a _story.md file."""

    story_id: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str
    description: str | None = None
    priority: Priority = Priority.MEDIUM
    tags: list[str] = Field(default_factory=list)
    scenarios: list[ScenarioSpec] = Field(default_factory=list)
    source_dir: Path | None = None


class FeatureSpec(BaseModel):
    """Feature specification parsed from a _feature.md file."""

    feature_id: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str
    description: str | None = None
    component: str | None = None
    owner: str | None = None
    priority: Priority = Priority.MEDIUM
    tags: list[str] = Field(default_factory=list)
    stories: list[StorySpec] = Field(default_factory=list)
    source_dir: Path | None = None

    @property
    def all_scenarios(self) -> list[ScenarioSpec]:
        scenarios: list[ScenarioSpec] = []
        for story in self.stories:
            scenarios.extend(story.scenarios)
        return scenarios


class SpecsConfig(BaseModel):
    """Root configuration containing all parsed features."""

    version: str = "2.0"
    features: list[FeatureSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> SpecsConfig:
        seen_scenario_ids: set[str] = set()
        for feature in self.features:
            for story in feature.stories:
                for scenario in story.scenarios:
                    if scenario.scenario_id in seen_scenario_ids:
                        raise ValueError(
                            f"Duplicate scenario_id: {scenario.scenario_id}"
                        )
                    seen_scenario_ids.add(scenario.scenario_id)
        return self

    @classmethod
    def from_directory(cls, features_dir: str | Path) -> SpecsConfig:
        from specleft.parser import SpecParser

        parser = SpecParser()
        return parser.parse_directory(Path(features_dir))

    def get_scenario(self, scenario_id: str) -> ScenarioSpec | None:
        for feature in self.features:
            for story in feature.stories:
                for scenario in story.scenarios:
                    if scenario.scenario_id == scenario_id:
                        return scenario
        return None

    def get_scenarios_by_tag(self, tag: str) -> list[ScenarioSpec]:
        return [
            scenario
            for feature in self.features
            for story in feature.stories
            for scenario in story.scenarios
            if tag in scenario.tags
        ]
