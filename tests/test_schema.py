"""Tests for specleft.schema module."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from specleft.schema import (
    ExecutionTime,
    FeatureSpec,
    Priority,
    ScenarioSpec,
    SpecDataRow,
    SpecStep,
    SpecsConfig,
    StepType,
    StorySpec,
)


class SpecStepType:
    """Tests for StepType enum."""

    def test_step_type_values(self) -> None:
        """Test that all BDD step types are defined."""
        assert StepType.GIVEN.value == "given"
        assert StepType.WHEN.value == "when"
        assert StepType.THEN.value == "then"
        assert StepType.AND.value == "and"
        assert StepType.BUT.value == "but"

    def test_step_type_from_string(self) -> None:
        """Test creating StepType from string value."""
        assert StepType("given") == StepType.GIVEN
        assert StepType("when") == StepType.WHEN
        assert StepType("then") == StepType.THEN
        assert StepType("and") == StepType.AND
        assert StepType("but") == StepType.BUT


class TestPriority:
    """Tests for Priority enum."""

    def test_priority_values(self) -> None:
        """Test that all priority levels are defined."""
        assert Priority.CRITICAL.value == "critical"
        assert Priority.HIGH.value == "high"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.LOW.value == "low"

    def test_priority_from_string(self) -> None:
        """Test creating Priority from string value."""
        assert Priority("critical") == Priority.CRITICAL
        assert Priority("low") == Priority.LOW


class TestExecutionTime:
    """Tests for ExecutionTime enum."""

    def test_execution_time_values(self) -> None:
        """Test that all execution time levels are defined."""
        assert ExecutionTime.FAST.value == "fast"
        assert ExecutionTime.MEDIUM.value == "medium"
        assert ExecutionTime.SLOW.value == "slow"


class SpecStepTests:
    """Tests for SpecStep model."""

    def test_minimal_step(self) -> None:
        """Test creating step with required fields only."""
        step = SpecStep(type=StepType.GIVEN, description=" user logs in ")
        assert step.type == StepType.GIVEN
        assert step.description == "user logs in"
        assert step.data == {}

    def test_empty_description_raises_error(self) -> None:
        """Test that empty description raises validation error."""
        with pytest.raises(ValidationError):
            SpecStep(type=StepType.GIVEN, description="")


class SpecDataRowTests:
    """Tests for SpecDataRow model."""

    def test_minimal_data_row(self) -> None:
        """Test creating data row with params only."""
        row = SpecDataRow(params={"username": "test"})
        assert row.params["username"] == "test"
        assert row.description is None

    def test_empty_params_raises_error(self) -> None:
        """Test that empty params raise validation error."""
        with pytest.raises(ValidationError):
            SpecDataRow(params={})


class TestScenarioSpec:
    """Tests for ScenarioSpec model."""

    def test_minimal_scenario(self) -> None:
        """Test creating scenario with required fields only."""
        scenario = ScenarioSpec(
            scenario_id="basic-scenario",
            name="Basic scenario",
        )
        assert scenario.priority == Priority.MEDIUM
        assert scenario.execution_time == ExecutionTime.FAST
        assert scenario.is_parameterized is False

    def test_parameterized_scenario(self) -> None:
        """Test parameterized scenario property."""
        scenario = ScenarioSpec(
            scenario_id="data-scenario",
            name="Data scenario",
            test_data=[SpecDataRow(params={"x": 1})],
        )
        assert scenario.is_parameterized is True

    def test_invalid_scenario_id_format(self) -> None:
        """Test that invalid scenario ID format raises error."""
        with pytest.raises(ValidationError):
            ScenarioSpec(scenario_id="INVALID", name="Test")


class TestStorySpec:
    """Tests for StorySpec model."""

    def test_minimal_story(self) -> None:
        """Test creating story with required fields only."""
        story = StorySpec(story_id="story", name="Story")
        assert story.priority == Priority.MEDIUM
        assert story.tags == []


class TestFeatureSpec:
    """Tests for FeatureSpec model."""

    def test_minimal_feature(self) -> None:
        """Test creating feature with required fields only."""
        feature = FeatureSpec(feature_id="calculator", name="Calculator")
        assert feature.priority == Priority.MEDIUM
        assert feature.tags == []

    def test_all_scenarios_property(self) -> None:
        """Test that all_scenarios aggregates nested scenarios."""
        scenario = ScenarioSpec(scenario_id="scenario", name="Scenario")
        story = StorySpec(story_id="story", name="Story", scenarios=[scenario])
        feature = FeatureSpec(
            feature_id="feature",
            name="Feature",
            stories=[story],
        )
        assert feature.all_scenarios == [scenario]


class TestSpecsConfig:
    """Tests for SpecsConfig model."""

    def test_duplicate_scenario_ids_raises_error(self) -> None:
        """Test that duplicate scenario IDs across specs raise error."""
        scenario = ScenarioSpec(scenario_id="scenario", name="Scenario")
        story = StorySpec(story_id="story", name="Story", scenarios=[scenario])
        feature = FeatureSpec(feature_id="feature", name="Feature", stories=[story])

        other_scenario = ScenarioSpec(scenario_id="scenario", name="Scenario 2")
        other_story = StorySpec(
            story_id="story-2", name="Story 2", scenarios=[other_scenario]
        )
        other_feature = FeatureSpec(
            feature_id="feature-2", name="Feature 2", stories=[other_story]
        )

        with pytest.raises(ValidationError):
            SpecsConfig(features=[feature, other_feature])

    def test_get_scenario(self) -> None:
        """Test lookup by scenario ID."""
        scenario = ScenarioSpec(scenario_id="scenario", name="Scenario")
        story = StorySpec(story_id="story", name="Story", scenarios=[scenario])
        feature = FeatureSpec(feature_id="feature", name="Feature", stories=[story])
        config = SpecsConfig(features=[feature])

        assert config.get_scenario("scenario") == scenario
        assert config.get_scenario("missing") is None

    def test_get_scenarios_by_tag(self) -> None:
        """Test filtering by tag."""
        scenario = ScenarioSpec(scenario_id="scenario", name="Scenario", tags=["smoke"])
        story = StorySpec(story_id="story", name="Story", scenarios=[scenario])
        feature = FeatureSpec(feature_id="feature", name="Feature", stories=[story])
        config = SpecsConfig(features=[feature])

        assert config.get_scenarios_by_tag("smoke") == [scenario]
        assert config.get_scenarios_by_tag("missing") == []
