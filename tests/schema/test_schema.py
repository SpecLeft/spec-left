"""Tests for specleft.schema module."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
import specleft.schema as schema
from pydantic import ValidationError
from specleft.schema import (
    ExecutionTime,
    FeatureSpec,
    Priority,
    ScenarioSpec,
    SpecDataRow,
    SpecsConfig,
    SpecStep,
    StepType,
    StorySpec,
)


class TestStepType:
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

    def test_step_type_is_string_enum(self) -> None:
        """Test that StepType is a str enum."""
        assert isinstance(StepType.GIVEN, str)
        assert StepType.GIVEN == "given"
        assert StepType.GIVEN.name == "GIVEN"

    def test_step_type_invalid_value(self) -> None:
        """Test that invalid step type raises ValueError."""
        with pytest.raises(ValueError):
            StepType("invalid")


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
        assert Priority("high") == Priority.HIGH
        assert Priority("medium") == Priority.MEDIUM
        assert Priority("low") == Priority.LOW

    def test_priority_is_string_enum(self) -> None:
        """Test that Priority is a str enum."""
        assert isinstance(Priority.HIGH, str)
        assert Priority.HIGH == "high"
        assert Priority.HIGH.name == "HIGH"

    def test_priority_invalid_value(self) -> None:
        """Test that invalid priority raises ValueError."""
        with pytest.raises(ValueError):
            Priority("invalid")


class TestExecutionTime:
    """Tests for ExecutionTime enum."""

    def test_execution_time_values(self) -> None:
        """Test that all execution time levels are defined."""
        assert ExecutionTime.FAST.value == "fast"
        assert ExecutionTime.MEDIUM.value == "medium"
        assert ExecutionTime.SLOW.value == "slow"

    def test_execution_time_from_string(self) -> None:
        """Test creating ExecutionTime from string value."""
        assert ExecutionTime("fast") == ExecutionTime.FAST
        assert ExecutionTime("medium") == ExecutionTime.MEDIUM
        assert ExecutionTime("slow") == ExecutionTime.SLOW

    def test_execution_time_is_string_enum(self) -> None:
        """Test that ExecutionTime is a str enum."""
        assert isinstance(ExecutionTime.FAST, str)
        assert ExecutionTime.FAST == "fast"
        assert ExecutionTime.FAST.name == "FAST"

    def test_execution_time_invalid_value(self) -> None:
        """Test that invalid execution time raises ValueError."""
        with pytest.raises(ValueError):
            ExecutionTime("invalid")


class TestSpecStep:
    """Tests for SpecStep model."""

    def test_minimal_step(self) -> None:
        """Test creating step with required fields only."""
        step = SpecStep(type=StepType.GIVEN, description="user logs in")
        assert step.type == StepType.GIVEN
        assert step.description == "user logs in"
        assert step.data == {}
        assert SpecStep.model_fields["data"].default_factory is not None

    def test_step_with_data(self) -> None:
        """Test creating step with data."""
        step = SpecStep(
            type=StepType.WHEN,
            description="user submits form",
            data={"field": "value", "count": 5},
        )
        assert step.type == StepType.WHEN
        assert step.description == "user submits form"
        assert step.data == {"field": "value", "count": 5}

    def test_description_strips_whitespace(self) -> None:
        """Test that description is stripped of whitespace."""
        step = SpecStep(type=StepType.GIVEN, description="  user logs in  ")
        assert step.description == "user logs in"

    def test_empty_description_raises_error(self) -> None:
        """Test that empty description raises validation error."""
        with pytest.raises(ValidationError):
            SpecStep(type=StepType.GIVEN, description="")

    def test_whitespace_only_description_gets_stripped(self) -> None:
        """Test that whitespace-only description gets stripped to empty."""
        # Note: The strip validator runs but min_length=1 on the field schema
        # doesn't re-validate after the validator runs. This is a Pydantic behavior.
        step = SpecStep(type=StepType.GIVEN, description="   ")
        assert step.description == ""

    def test_step_with_all_step_types(self) -> None:
        """Test creating steps with all step types."""
        for step_type in StepType:
            step = SpecStep(type=step_type, description="test step")
            assert step.type == step_type

    def test_step_with_string_type(self) -> None:
        """Test creating step with string type value."""
        step = SpecStep(type="given", description="test step")
        assert step.type == StepType.GIVEN


class TestSpecDataRow:
    """Tests for SpecDataRow model."""

    def test_minimal_data_row(self) -> None:
        """Test creating data row with params only."""
        row = SpecDataRow(params={"username": "test"})
        assert row.params["username"] == "test"
        assert row.description is None

    def test_data_row_with_description(self) -> None:
        """Test creating data row with description."""
        row = SpecDataRow(params={"x": 1}, description="test case 1")
        assert row.params == {"x": 1}
        assert row.description == "test case 1"

    def test_data_row_with_multiple_params(self) -> None:
        """Test creating data row with multiple params."""
        row = SpecDataRow(
            params={"username": "admin", "password": "secret", "role": "admin"}
        )
        assert row.params["username"] == "admin"
        assert row.params["password"] == "secret"
        assert row.params["role"] == "admin"

    def test_empty_params_raises_error(self) -> None:
        """Test that empty params raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            SpecDataRow(params={})
        assert "Test data params cannot be empty" in str(exc_info.value)

    def test_data_row_params_with_various_types(self) -> None:
        """Test that params can contain various types."""
        row = SpecDataRow(
            params={
                "string": "value",
                "number": 42,
                "float": 3.14,
                "boolean": True,
                "list": [1, 2, 3],
                "dict": {"nested": "value"},
            }
        )
        assert row.params["string"] == "value"
        assert row.params["number"] == 42
        assert row.params["float"] == 3.14
        assert row.params["boolean"] is True
        assert row.params["list"] == [1, 2, 3]
        assert row.params["dict"] == {"nested": "value"}


class TestScenarioSpec:
    """Tests for ScenarioSpec model."""

    def test_minimal_scenario(self) -> None:
        """Test creating scenario with required fields only."""
        scenario = ScenarioSpec(
            scenario_id="basic-scenario",
            name="Basic scenario",
        )
        assert scenario.scenario_id == "basic-scenario"
        assert scenario.name == "Basic scenario"
        assert scenario.description is None
        assert scenario.priority is None  # Nullable in Phase 3
        assert scenario.priority_raw is None
        assert scenario.tags == []
        assert scenario.execution_time == ExecutionTime.FAST
        assert scenario.steps == []
        assert scenario.test_data == []
        assert scenario.source_file is None
        assert scenario.raw_metadata == {}
        assert ScenarioSpec.model_fields["raw_metadata"].default_factory is not None

    def test_scenario_with_all_fields(self) -> None:
        """Test creating scenario with all fields."""
        step = SpecStep(type=StepType.GIVEN, description="test step")
        data_row = SpecDataRow(params={"x": 1})
        source = Path("/path/to/spec.md")

        scenario = ScenarioSpec(
            scenario_id="full-scenario",
            name="Full Scenario",
            description="A complete scenario",
            priority=Priority.HIGH,
            priority_raw=Priority.LOW,
            tags=["smoke", "regression"],
            execution_time=ExecutionTime.SLOW,
            steps=[step],
            test_data=[data_row],
            source_file=source,
        )

        assert scenario.scenario_id == "full-scenario"
        assert scenario.name == "Full Scenario"
        assert scenario.description == "A complete scenario"
        assert scenario.priority == Priority.HIGH
        assert scenario.priority_raw == Priority.LOW
        assert scenario.tags == ["smoke", "regression"]
        assert scenario.execution_time == ExecutionTime.SLOW
        assert scenario.steps == [step]
        assert scenario.test_data == [data_row]
        assert scenario.source_file == source

    def test_is_parameterized_false(self) -> None:
        """Test is_parameterized returns False when no test_data."""
        scenario = ScenarioSpec(
            scenario_id="non-param",
            name="Non-parameterized",
        )
        assert scenario.is_parameterized is False

    def test_is_parameterized_true(self) -> None:
        """Test is_parameterized returns True when test_data exists."""
        scenario = ScenarioSpec(
            scenario_id="param-scenario",
            name="Parameterized scenario",
            test_data=[SpecDataRow(params={"x": 1})],
        )
        assert scenario.is_parameterized is True

    def test_test_function_name(self) -> None:
        """Test test_function_name property."""
        scenario = ScenarioSpec(
            scenario_id="my-test-scenario",
            name="My Test Scenario",
        )
        assert scenario.test_function_name == "test_my_test_scenario"

    def test_test_function_name_no_dashes(self) -> None:
        """Test test_function_name with no dashes."""
        scenario = ScenarioSpec(
            scenario_id="simple",
            name="Simple",
        )
        assert scenario.test_function_name == "test_simple"

    def test_invalid_scenario_id_uppercase(self) -> None:
        """Test that uppercase scenario ID raises error."""
        with pytest.raises(ValidationError):
            ScenarioSpec(scenario_id="INVALID", name="Test")

    def test_invalid_scenario_id_underscore(self) -> None:
        """Test that underscore in scenario ID raises error."""
        with pytest.raises(ValidationError):
            ScenarioSpec(scenario_id="invalid_id", name="Test")

    def test_invalid_scenario_id_space(self) -> None:
        """Test that space in scenario ID raises error."""
        with pytest.raises(ValidationError):
            ScenarioSpec(scenario_id="invalid id", name="Test")

    def test_valid_scenario_id_with_numbers(self) -> None:
        """Test that scenario ID with numbers is valid."""
        scenario = ScenarioSpec(scenario_id="test-123", name="Test")
        assert scenario.scenario_id == "test-123"

    def test_scenario_with_string_priority(self) -> None:
        """Test creating scenario with string priority."""
        scenario = ScenarioSpec(
            scenario_id="test",
            name="Test",
            priority="high",
        )
        assert scenario.priority == Priority.HIGH

    def test_scenario_with_string_execution_time(self) -> None:
        """Test creating scenario with string execution time."""
        scenario = ScenarioSpec(
            scenario_id="test",
            name="Test",
            execution_time="slow",
        )
        assert scenario.execution_time == ExecutionTime.SLOW


class TestStorySpec:
    """Tests for StorySpec model."""

    def test_minimal_story(self) -> None:
        """Test creating story with required fields only."""
        story = StorySpec(story_id="story", name="Story")
        assert story.story_id == "story"
        assert story.name == "Story"
        assert story.description is None
        assert story.priority == Priority.MEDIUM
        assert story.tags == []
        assert story.scenarios == []
        assert story.source_dir is None

    def test_story_with_all_fields(self) -> None:
        """Test creating story with all fields."""
        scenario = ScenarioSpec(scenario_id="scenario", name="Scenario")
        source = Path("/path/to/story")

        story = StorySpec(
            story_id="full-story",
            name="Full Story",
            description="A complete story",
            priority=Priority.CRITICAL,
            tags=["epic", "mvp"],
            scenarios=[scenario],
            source_dir=source,
        )

        assert story.story_id == "full-story"
        assert story.name == "Full Story"
        assert story.description == "A complete story"
        assert story.priority == Priority.CRITICAL
        assert story.tags == ["epic", "mvp"]
        assert story.scenarios == [scenario]
        assert story.source_dir == source
        assert StorySpec.model_fields["tags"].default_factory is not None

    def test_story_with_multiple_scenarios(self) -> None:
        """Test story with multiple scenarios."""
        scenarios = [
            ScenarioSpec(scenario_id="scenario-1", name="Scenario 1"),
            ScenarioSpec(scenario_id="scenario-2", name="Scenario 2"),
            ScenarioSpec(scenario_id="scenario-3", name="Scenario 3"),
        ]
        story = StorySpec(story_id="multi", name="Multi", scenarios=scenarios)
        assert len(story.scenarios) == 3

    def test_invalid_story_id_uppercase(self) -> None:
        """Test that uppercase story ID raises error."""
        with pytest.raises(ValidationError):
            StorySpec(story_id="INVALID", name="Test")

    def test_story_with_string_priority(self) -> None:
        """Test creating story with string priority."""
        story = StorySpec(story_id="test", name="Test", priority="low")
        assert story.priority == Priority.LOW


class TestFeatureSpec:
    """Tests for FeatureSpec model."""

    def test_minimal_feature(self) -> None:
        """Test creating feature with required fields only."""
        feature = FeatureSpec(feature_id="calculator", name="Calculator")
        assert feature.feature_id == "calculator"
        assert feature.name == "Calculator"
        assert feature.description is None
        assert feature.component is None
        assert feature.owner is None
        assert feature.priority == Priority.MEDIUM
        assert feature.tags == []
        assert feature.stories == []
        assert feature.source_dir is None

    def test_feature_with_all_fields(self) -> None:
        """Test creating feature with all fields."""
        scenario = ScenarioSpec(scenario_id="scenario", name="Scenario")
        story = StorySpec(story_id="story", name="Story", scenarios=[scenario])
        source = Path("/path/to/feature")

        feature = FeatureSpec(
            feature_id="full-feature",
            name="Full Feature",
            description="A complete feature",
            component="core",
            owner="team-a",
            priority=Priority.HIGH,
            tags=["v1", "release"],
            stories=[story],
            source_dir=source,
            confidence="high",
            source="docs",
            assumptions=["assumption"],
            open_questions=["question"],
        )

        assert feature.feature_id == "full-feature"
        assert feature.name == "Full Feature"
        assert feature.description == "A complete feature"
        assert feature.component == "core"
        assert feature.owner == "team-a"
        assert feature.priority == Priority.HIGH
        assert feature.tags == ["v1", "release"]
        assert feature.stories == [story]
        assert feature.source_dir == source
        assert feature.confidence == "high"
        assert feature.source == "docs"
        assert feature.assumptions == ["assumption"]
        assert feature.open_questions == ["question"]

    def test_all_scenarios_empty(self) -> None:
        """Test all_scenarios with no stories."""
        feature = FeatureSpec(feature_id="empty", name="Empty")
        assert feature.all_scenarios == []

    def test_all_scenarios_single_story(self) -> None:
        """Test all_scenarios with single story."""
        scenario = ScenarioSpec(scenario_id="scenario", name="Scenario")
        story = StorySpec(story_id="story", name="Story", scenarios=[scenario])
        feature = FeatureSpec(feature_id="feature", name="Feature", stories=[story])
        assert feature.all_scenarios == [scenario]

    def test_all_scenarios_multiple_stories(self) -> None:
        """Test all_scenarios aggregates from multiple stories."""
        scenario1 = ScenarioSpec(scenario_id="scenario-1", name="Scenario 1")
        scenario2 = ScenarioSpec(scenario_id="scenario-2", name="Scenario 2")
        scenario3 = ScenarioSpec(scenario_id="scenario-3", name="Scenario 3")

        story1 = StorySpec(story_id="story-1", name="Story 1", scenarios=[scenario1])
        story2 = StorySpec(
            story_id="story-2", name="Story 2", scenarios=[scenario2, scenario3]
        )

        feature = FeatureSpec(
            feature_id="feature", name="Feature", stories=[story1, story2]
        )

        assert feature.all_scenarios == [scenario1, scenario2, scenario3]

    def test_invalid_feature_id_uppercase(self) -> None:
        """Test that uppercase feature ID raises error."""
        with pytest.raises(ValidationError):
            FeatureSpec(feature_id="INVALID", name="Test")

    def test_feature_with_string_priority(self) -> None:
        """Test creating feature with string priority."""
        feature = FeatureSpec(feature_id="test", name="Test", priority="critical")
        assert feature.priority == Priority.CRITICAL


class TestSpecsConfig:
    """Tests for SpecsConfig model."""

    def test_empty_config(self) -> None:
        """Test creating empty config."""
        config = SpecsConfig()
        assert config.version == "2.0"
        assert config.features == []
        assert SpecsConfig.model_fields["features"].default_factory is not None

    def test_config_with_custom_version(self) -> None:
        """Test config with custom version."""
        config = SpecsConfig(version="1.0")
        assert config.version == "1.0"

    def test_config_with_features(self) -> None:
        """Test config with features."""
        feature = FeatureSpec(feature_id="feature", name="Feature")
        config = SpecsConfig(features=[feature])
        assert config.features == [feature]

    def test_duplicate_scenario_ids_allowed(self) -> None:
        """Test that duplicate scenario IDs are permitted in config."""
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

        config = SpecsConfig(features=[feature, other_feature])
        assert config.features

    def test_unique_scenario_ids_valid(self) -> None:
        """Test that unique scenario IDs are valid."""
        scenarios = [
            ScenarioSpec(scenario_id=f"scenario-{i}", name=f"Scenario {i}")
            for i in range(5)
        ]
        story = StorySpec(story_id="story", name="Story", scenarios=scenarios)
        feature = FeatureSpec(feature_id="feature", name="Feature", stories=[story])
        config = SpecsConfig(features=[feature])
        assert len(config.features) == 1

    def test_get_scenario_found(self) -> None:
        """Test lookup by scenario ID when found."""
        scenario = ScenarioSpec(scenario_id="target", name="Target Scenario")
        story = StorySpec(story_id="story", name="Story", scenarios=[scenario])
        feature = FeatureSpec(feature_id="feature", name="Feature", stories=[story])
        config = SpecsConfig(features=[feature])

        result = config.get_scenario("target")
        assert result == scenario

    def test_get_scenario_not_found(self) -> None:
        """Test lookup by scenario ID when not found."""
        scenario = ScenarioSpec(scenario_id="existing", name="Existing")
        story = StorySpec(story_id="story", name="Story", scenarios=[scenario])
        feature = FeatureSpec(feature_id="feature", name="Feature", stories=[story])
        config = SpecsConfig(features=[feature])

        result = config.get_scenario("missing")
        assert result is None

    def test_get_scenario_empty_config(self) -> None:
        """Test lookup in empty config."""
        config = SpecsConfig()
        result = config.get_scenario("any")
        assert result is None

    def test_get_scenario_nested_deep(self) -> None:
        """Test lookup finds scenario in nested structure."""
        target = ScenarioSpec(scenario_id="deep-target", name="Deep Target")
        other_scenario = ScenarioSpec(scenario_id="other", name="Other")

        story1 = StorySpec(
            story_id="story-1", name="Story 1", scenarios=[other_scenario]
        )
        story2 = StorySpec(story_id="story-2", name="Story 2", scenarios=[target])

        feature1 = FeatureSpec(
            feature_id="feature-1", name="Feature 1", stories=[story1]
        )
        feature2 = FeatureSpec(
            feature_id="feature-2", name="Feature 2", stories=[story2]
        )

        config = SpecsConfig(features=[feature1, feature2])

        result = config.get_scenario("deep-target")
        assert result == target

    def test_get_scenarios_by_tag_found(self) -> None:
        """Test filtering by tag when matches exist."""
        scenario1 = ScenarioSpec(
            scenario_id="scenario-1", name="Scenario 1", tags=["smoke", "fast"]
        )
        scenario2 = ScenarioSpec(
            scenario_id="scenario-2", name="Scenario 2", tags=["regression"]
        )
        scenario3 = ScenarioSpec(
            scenario_id="scenario-3", name="Scenario 3", tags=["smoke"]
        )

        story = StorySpec(
            story_id="story",
            name="Story",
            scenarios=[scenario1, scenario2, scenario3],
        )
        feature = FeatureSpec(feature_id="feature", name="Feature", stories=[story])
        config = SpecsConfig(features=[feature])

        result = config.get_scenarios_by_tag("smoke")
        assert result == [scenario1, scenario3]

    def test_get_scenarios_by_tag_not_found(self) -> None:
        """Test filtering by tag when no matches."""
        scenario = ScenarioSpec(
            scenario_id="scenario", name="Scenario", tags=["regression"]
        )
        story = StorySpec(story_id="story", name="Story", scenarios=[scenario])
        feature = FeatureSpec(feature_id="feature", name="Feature", stories=[story])
        config = SpecsConfig(features=[feature])

        result = config.get_scenarios_by_tag("smoke")
        assert result == []

    def test_get_scenarios_by_tag_empty_config(self) -> None:
        """Test filtering by tag in empty config."""
        config = SpecsConfig()
        result = config.get_scenarios_by_tag("any")
        assert result == []

    def test_get_scenarios_by_tag_across_features(self) -> None:
        """Test filtering by tag across multiple features."""
        scenario1 = ScenarioSpec(
            scenario_id="scenario-1", name="Scenario 1", tags=["critical"]
        )
        scenario2 = ScenarioSpec(
            scenario_id="scenario-2", name="Scenario 2", tags=["critical"]
        )

        story1 = StorySpec(story_id="story-1", name="Story 1", scenarios=[scenario1])
        story2 = StorySpec(story_id="story-2", name="Story 2", scenarios=[scenario2])

        feature1 = FeatureSpec(
            feature_id="feature-1", name="Feature 1", stories=[story1]
        )
        feature2 = FeatureSpec(
            feature_id="feature-2", name="Feature 2", stories=[story2]
        )

        config = SpecsConfig(features=[feature1, feature2])

        result = config.get_scenarios_by_tag("critical")
        assert result == [scenario1, scenario2]

    def test_from_directory(self, tmp_path: Path) -> None:
        """Test loading config from directory."""
        # Create a minimal feature structure
        feature_dir = tmp_path / "test-feature"
        feature_dir.mkdir()

        # Create _feature.md
        feature_md = feature_dir / "_feature.md"
        feature_md.write_text("# Feature: test-feature\n\nTest feature description\n")

        # Create story directory with _story.md
        story_dir = feature_dir / "test-story"
        story_dir.mkdir()
        story_md = story_dir / "_story.md"
        story_md.write_text("# Story: test-story\n\nTest story description\n")

        # Create scenario file
        scenario_md = story_dir / "test-scenario.md"
        scenario_md.write_text(
            "# Scenario: test-scenario\n\n"
            "Test scenario description\n\n"
            "## Steps\n\n"
            "- Given a precondition\n"
            "- When an action occurs\n"
            "- Then a result is expected\n"
        )

        # Load from directory
        config = SpecsConfig.from_directory(tmp_path)

        assert len(config.features) == 1
        assert config.features[0].feature_id == "test-feature"
        assert len(config.features[0].stories) == 1
        assert config.features[0].stories[0].story_id == "test-story"

    def test_feature_raw_metadata_defaults(self) -> None:
        """Test raw_metadata default for FeatureSpec."""
        feature = FeatureSpec(feature_id="feature", name="Feature")
        assert feature.raw_metadata == {}

    def test_scenario_raw_metadata_defaults(self) -> None:
        """Test raw_metadata default for ScenarioSpec."""
        scenario = ScenarioSpec(scenario_id="scenario", name="Scenario")
        assert scenario.raw_metadata == {}

    def test_story_tags_default_factory(self) -> None:
        """Test tags default factory on StorySpec."""
        story = StorySpec(story_id="story", name="Story")
        assert story.tags == []
        assert StorySpec.model_fields["tags"].default_factory is not None

    def test_story_description_defaults(self) -> None:
        """Test StorySpec description defaults to None."""
        story = StorySpec(story_id="story", name="Story")
        assert story.description is None


class TestSchemaModuleReload:
    """Tests for module-level execution coverage."""

    def test_schema_module_reload(self) -> None:
        """Test module reload executes top-level definitions."""
        module = importlib.reload(schema)
        assert module.StepType.GIVEN.value == "given"
