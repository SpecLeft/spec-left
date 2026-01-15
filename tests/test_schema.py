"""Tests for specleft.schema module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from specleft.schema import (
    ExecutionSpeed,
    ExternalReference,
    Feature,
    FeatureMetadata,
    FeaturesConfig,
    Priority,
    Scenario,
    ScenarioMetadata,
    StepMetadata,
    StepType,
    TestDataRow,
    TestStep,
    TestType,
)


class TestStepType:
    """Tests for StepType enum."""

    def test_step_type_values(self) -> None:
        """Test that all BDD step types are defined."""
        assert StepType.GIVEN.value == "given"
        assert StepType.WHEN.value == "when"
        assert StepType.THEN.value == "then"
        assert StepType.AND.value == "and"

    def test_step_type_from_string(self) -> None:
        """Test creating StepType from string value."""
        assert StepType("given") == StepType.GIVEN
        assert StepType("when") == StepType.WHEN
        assert StepType("then") == StepType.THEN
        assert StepType("and") == StepType.AND


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


class TestExecutionSpeed:
    """Tests for ExecutionSpeed enum."""

    def test_execution_speed_values(self) -> None:
        """Test that all execution speed levels are defined."""
        assert ExecutionSpeed.FAST.value == "fast"
        assert ExecutionSpeed.MEDIUM.value == "medium"
        assert ExecutionSpeed.SLOW.value == "slow"


class TestTestType:
    """Tests for TestType enum."""

    def test_test_type_values(self) -> None:
        """Test that all test types are defined."""
        assert TestType.SMOKE.value == "smoke"
        assert TestType.REGRESSION.value == "regression"
        assert TestType.INTEGRATION.value == "integration"
        assert TestType.E2E.value == "e2e"
        assert TestType.PERFORMANCE.value == "performance"
        assert TestType.UNIT.value == "unit"


class TestExternalReference:
    """Tests for ExternalReference model."""

    def test_minimal_external_reference(self) -> None:
        """Test creating external reference with required fields only."""
        ref = ExternalReference(system="jira", id="AUTH-123")
        assert ref.system == "jira"
        assert ref.id == "AUTH-123"
        assert ref.url is None

    def test_full_external_reference(self) -> None:
        """Test creating external reference with all fields."""
        ref = ExternalReference(
            system="github",
            id="42",
            url="https://github.com/org/repo/issues/42",
        )
        assert ref.system == "github"
        assert ref.id == "42"
        assert str(ref.url) == "https://github.com/org/repo/issues/42"

    def test_invalid_url_raises_error(self) -> None:
        """Test that invalid URL raises validation error."""
        with pytest.raises(ValidationError):
            ExternalReference(system="jira", id="123", url="not-a-url")


class TestStepMetadata:
    """Tests for StepMetadata model."""

    def test_default_values(self) -> None:
        """Test that default values are applied."""
        meta = StepMetadata()
        assert meta.timeout_seconds is None
        assert meta.retry_on_failure is False
        assert meta.continue_on_failure is False
        assert meta.custom == {}

    def test_custom_metadata(self) -> None:
        """Test adding custom metadata."""
        meta = StepMetadata(
            timeout_seconds=30,
            retry_on_failure=True,
            custom={"screenshot": True, "retries": 3},
        )
        assert meta.timeout_seconds == 30
        assert meta.retry_on_failure is True
        assert meta.custom["screenshot"] is True

    def test_invalid_timeout_raises_error(self) -> None:
        """Test that zero or negative timeout raises error."""
        with pytest.raises(ValidationError):
            StepMetadata(timeout_seconds=0)
        with pytest.raises(ValidationError):
            StepMetadata(timeout_seconds=-1)


class TestScenarioMetadata:
    """Tests for ScenarioMetadata model."""

    def test_default_values(self) -> None:
        """Test that default values are applied."""
        meta = ScenarioMetadata()
        assert meta.test_type is None
        assert meta.execution_time == ExecutionSpeed.MEDIUM
        assert meta.dependencies == []
        assert meta.external_references == []
        assert meta.author is None
        assert meta.flaky is False
        assert meta.skip is False

    def test_full_metadata(self) -> None:
        """Test creating metadata with all fields."""
        ref = ExternalReference(system="jira", id="AUTH-123")
        meta = ScenarioMetadata(
            test_type=TestType.SMOKE,
            execution_time=ExecutionSpeed.FAST,
            dependencies=["database", "redis"],
            external_references=[ref],
            author="test@example.com",
            created_date="2025-01-14",
            flaky=True,
            skip=True,
            skip_reason="Known issue",
            custom={"env": "staging"},
        )
        assert meta.test_type == TestType.SMOKE
        assert meta.execution_time == ExecutionSpeed.FAST
        assert "database" in meta.dependencies
        assert len(meta.external_references) == 1
        assert meta.flaky is True
        assert meta.skip_reason == "Known issue"


class TestFeatureMetadata:
    """Tests for FeatureMetadata model."""

    def test_default_values(self) -> None:
        """Test that default values are applied."""
        meta = FeatureMetadata()
        assert meta.owner is None
        assert meta.component is None
        assert meta.priority == Priority.MEDIUM
        assert meta.tags == []
        assert meta.external_references == []
        assert meta.links == {}
        assert meta.custom == {}

    def test_full_metadata(self) -> None:
        """Test creating metadata with all fields."""
        ref = ExternalReference(system="jira", id="FEAT-100")
        meta = FeatureMetadata(
            owner="auth-team",
            component="authentication",
            priority=Priority.CRITICAL,
            tags=["security", "auth"],
            external_references=[ref],
            links={"docs": "https://docs.example.com/auth"},
            custom={"compliance": ["SOC2", "HIPAA"]},
        )
        assert meta.owner == "auth-team"
        assert meta.priority == Priority.CRITICAL
        assert "security" in meta.tags
        assert str(meta.links["docs"]) == "https://docs.example.com/auth"


class TestTestStep:
    """Tests for TestStep model."""

    def test_minimal_step(self) -> None:
        """Test creating step with required fields only."""
        step = TestStep(type=StepType.GIVEN, description="user is on login page")
        assert step.type == StepType.GIVEN
        assert step.description == "user is on login page"
        assert step.metadata is None

    def test_step_with_metadata(self) -> None:
        """Test creating step with metadata."""
        meta = StepMetadata(timeout_seconds=10)
        step = TestStep(
            type=StepType.WHEN,
            description="user enters credentials",
            metadata=meta,
        )
        assert step.metadata is not None
        assert step.metadata.timeout_seconds == 10

    def test_empty_description_raises_error(self) -> None:
        """Test that empty description raises validation error."""
        with pytest.raises(ValidationError):
            TestStep(type=StepType.GIVEN, description="")


class TestTestDataRow:
    """Tests for TestDataRow model."""

    def test_minimal_data_row(self) -> None:
        """Test creating data row with params only."""
        row = TestDataRow(params={"username": "test", "password": "secret"})
        assert row.params["username"] == "test"
        assert row.description is None
        assert row.metadata is None

    def test_full_data_row(self) -> None:
        """Test creating data row with all fields."""
        row = TestDataRow(
            params={"username": "admin", "password": "admin123"},
            description="Admin user credentials",
            metadata={"source": "test-data.csv"},
        )
        assert row.description == "Admin user credentials"
        assert row.metadata["source"] == "test-data.csv"


class TestScenario:
    """Tests for Scenario model."""

    def test_minimal_scenario(self) -> None:
        """Test creating scenario with required fields only."""
        step = TestStep(type=StepType.WHEN, description="something happens")
        scenario = Scenario(
            id="test-scenario",
            name="Test Scenario",
            steps=[step],
        )
        assert scenario.id == "test-scenario"
        assert scenario.name == "Test Scenario"
        assert scenario.priority == Priority.MEDIUM
        assert scenario.tags == []
        assert len(scenario.steps) == 1

    def test_full_scenario(self) -> None:
        """Test creating scenario with all fields."""
        steps = [
            TestStep(type=StepType.GIVEN, description="setup"),
            TestStep(type=StepType.WHEN, description="action"),
            TestStep(type=StepType.THEN, description="assertion"),
        ]
        data = [
            TestDataRow(params={"x": 1, "y": 2}),
            TestDataRow(params={"x": 3, "y": 4}),
        ]
        meta = ScenarioMetadata(test_type=TestType.UNIT)
        scenario = Scenario(
            id="full-scenario",
            name="Full Scenario",
            description="A complete scenario",
            priority=Priority.HIGH,
            tags=["smoke", "regression"],
            metadata=meta,
            steps=steps,
            test_data=data,
        )
        assert scenario.description == "A complete scenario"
        assert scenario.priority == Priority.HIGH
        assert len(scenario.tags) == 2
        assert len(scenario.test_data) == 2

    def test_invalid_scenario_id_format(self) -> None:
        """Test that invalid scenario ID format raises error."""
        step = TestStep(type=StepType.WHEN, description="action")

        # Uppercase not allowed
        with pytest.raises(ValidationError):
            Scenario(id="TEST-SCENARIO", name="Test", steps=[step])

        # Underscores not allowed
        with pytest.raises(ValidationError):
            Scenario(id="test_scenario", name="Test", steps=[step])

        # Spaces not allowed
        with pytest.raises(ValidationError):
            Scenario(id="test scenario", name="Test", steps=[step])

    def test_valid_scenario_id_formats(self) -> None:
        """Test that valid scenario ID formats are accepted."""
        step = TestStep(type=StepType.WHEN, description="action")

        # Lowercase with hyphens
        s1 = Scenario(id="login-success", name="Test", steps=[step])
        assert s1.id == "login-success"

        # Lowercase with numbers
        s2 = Scenario(id="test123", name="Test", steps=[step])
        assert s2.id == "test123"

        # Mixed lowercase, numbers, and hyphens
        s3 = Scenario(id="api-v2-auth", name="Test", steps=[step])
        assert s3.id == "api-v2-auth"


class TestFeature:
    """Tests for Feature model."""

    def test_minimal_feature(self) -> None:
        """Test creating feature with required fields only."""
        step = TestStep(type=StepType.WHEN, description="action")
        scenario = Scenario(id="test", name="Test", steps=[step])
        feature = Feature(
            id="AUTH-001",
            name="Authentication",
            scenarios=[scenario],
        )
        assert feature.id == "AUTH-001"
        assert feature.name == "Authentication"
        assert feature.description is None
        assert feature.metadata is None
        assert len(feature.scenarios) == 1

    def test_full_feature(self) -> None:
        """Test creating feature with all fields."""
        step = TestStep(type=StepType.WHEN, description="action")
        scenario = Scenario(id="test", name="Test", steps=[step])
        meta = FeatureMetadata(owner="auth-team", priority=Priority.CRITICAL)
        feature = Feature(
            id="AUTH-001",
            name="Authentication",
            description="User authentication feature",
            metadata=meta,
            scenarios=[scenario],
        )
        assert feature.description == "User authentication feature"
        assert feature.metadata.owner == "auth-team"

    def test_invalid_feature_id_format(self) -> None:
        """Test that invalid feature ID format raises error."""
        step = TestStep(type=StepType.WHEN, description="action")
        scenario = Scenario(id="test", name="Test", steps=[step])

        # Lowercase not allowed
        with pytest.raises(ValidationError):
            Feature(id="auth-001", name="Test", scenarios=[scenario])

        # Spaces not allowed
        with pytest.raises(ValidationError):
            Feature(id="AUTH 001", name="Test", scenarios=[scenario])

    def test_valid_feature_id_formats(self) -> None:
        """Test that valid feature ID formats are accepted."""
        step = TestStep(type=StepType.WHEN, description="action")
        scenario = Scenario(id="test", name="Test", steps=[step])

        # Uppercase with hyphens
        f1 = Feature(id="AUTH-001", name="Test", scenarios=[scenario])
        assert f1.id == "AUTH-001"

        # Numbers only
        f2 = Feature(id="001", name="Test", scenarios=[scenario])
        assert f2.id == "001"

        # Uppercase letters only
        f3 = Feature(id="AUTH", name="Test", scenarios=[scenario])
        assert f3.id == "AUTH"

    def test_duplicate_scenario_ids_raises_error(self) -> None:
        """Test that duplicate scenario IDs within a feature raise error."""
        step = TestStep(type=StepType.WHEN, description="action")
        scenario1 = Scenario(id="test", name="Test 1", steps=[step])
        scenario2 = Scenario(id="test", name="Test 2", steps=[step])

        with pytest.raises(ValidationError) as exc_info:
            Feature(id="FEAT-001", name="Feature", scenarios=[scenario1, scenario2])

        assert "Duplicate scenario IDs" in str(exc_info.value)


class TestFeaturesConfig:
    """Tests for FeaturesConfig model."""

    def test_minimal_config(self) -> None:
        """Test creating config with required fields only."""
        step = TestStep(type=StepType.WHEN, description="action")
        scenario = Scenario(id="test", name="Test", steps=[step])
        feature = Feature(id="AUTH-001", name="Auth", scenarios=[scenario])

        config = FeaturesConfig(features=[feature])
        assert config.version == "1.0"
        assert len(config.features) == 1

    def test_custom_version(self) -> None:
        """Test creating config with custom version."""
        step = TestStep(type=StepType.WHEN, description="action")
        scenario = Scenario(id="test", name="Test", steps=[step])
        feature = Feature(id="AUTH-001", name="Auth", scenarios=[scenario])

        config = FeaturesConfig(version="2.0", features=[feature])
        assert config.version == "2.0"

    def test_duplicate_feature_ids_raises_error(self) -> None:
        """Test that duplicate feature IDs raise error."""
        step = TestStep(type=StepType.WHEN, description="action")
        scenario = Scenario(id="test", name="Test", steps=[step])
        feature1 = Feature(id="AUTH-001", name="Auth 1", scenarios=[scenario])
        feature2 = Feature(id="AUTH-001", name="Auth 2", scenarios=[scenario])

        with pytest.raises(ValidationError) as exc_info:
            FeaturesConfig(features=[feature1, feature2])

        assert "Duplicate feature IDs" in str(exc_info.value)

    def test_from_file_valid_json(self) -> None:
        """Test loading valid features.json file."""
        data = {
            "version": "1.0",
            "features": [
                {
                    "id": "AUTH-001",
                    "name": "Authentication",
                    "scenarios": [
                        {
                            "id": "login",
                            "name": "Login Test",
                            "steps": [
                                {"type": "given", "description": "user on login page"},
                                {"type": "when", "description": "enters credentials"},
                                {"type": "then", "description": "logged in"},
                            ],
                        }
                    ],
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            filepath = f.name

        try:
            config = FeaturesConfig.from_file(filepath)
            assert config.version == "1.0"
            assert len(config.features) == 1
            assert config.features[0].id == "AUTH-001"
        finally:
            Path(filepath).unlink()

    def test_from_file_not_found(self) -> None:
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            FeaturesConfig.from_file("/nonexistent/path/features.json")

        assert "Features file not found" in str(exc_info.value)

    def test_from_file_invalid_json(self) -> None:
        """Test that JSONDecodeError is raised for invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json {")
            filepath = f.name

        try:
            with pytest.raises(json.JSONDecodeError):
                FeaturesConfig.from_file(filepath)
        finally:
            Path(filepath).unlink()

    def test_from_file_validation_error(self) -> None:
        """Test that ValidationError is raised for schema violations."""
        data = {
            "version": "1.0",
            "features": [
                {
                    "id": "invalid-lowercase",  # Should be uppercase
                    "name": "Test",
                    "scenarios": [
                        {
                            "id": "test",
                            "name": "Test",
                            "steps": [{"type": "when", "description": "action"}],
                        }
                    ],
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            filepath = f.name

        try:
            with pytest.raises(ValidationError):
                FeaturesConfig.from_file(filepath)
        finally:
            Path(filepath).unlink()


class TestComplexFeatures:
    """Tests for complex features.json structures."""

    def test_full_featured_config(self) -> None:
        """Test creating a fully-featured configuration."""
        data = {
            "version": "1.0",
            "features": [
                {
                    "id": "AUTH-001",
                    "name": "User Authentication",
                    "description": "Authentication features",
                    "metadata": {
                        "owner": "auth-team",
                        "component": "authentication",
                        "priority": "critical",
                        "tags": ["security"],
                        "external_references": [
                            {
                                "system": "jira",
                                "id": "AUTH-100",
                                "url": "https://jira.example.com/AUTH-100",
                            }
                        ],
                        "links": {"docs": "https://docs.example.com/auth"},
                        "custom": {"compliance": ["SOC2"]},
                    },
                    "scenarios": [
                        {
                            "id": "login-success",
                            "name": "Successful Login",
                            "description": "User can log in with valid credentials",
                            "priority": "critical",
                            "tags": ["smoke", "auth"],
                            "metadata": {
                                "test_type": "smoke",
                                "execution_time": "fast",
                                "dependencies": ["database", "auth-service"],
                                "author": "test@example.com",
                            },
                            "steps": [
                                {"type": "given", "description": "user on login page"},
                                {
                                    "type": "when",
                                    "description": "enters credentials",
                                    "metadata": {"timeout_seconds": 10},
                                },
                                {"type": "then", "description": "sees dashboard"},
                            ],
                            "test_data": [
                                {
                                    "params": {
                                        "username": "user1",
                                        "password": "pass1",
                                    },
                                    "description": "Standard user",
                                },
                                {
                                    "params": {
                                        "username": "admin",
                                        "password": "admin",
                                    },
                                    "description": "Admin user",
                                },
                            ],
                        }
                    ],
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            filepath = f.name

        try:
            config = FeaturesConfig.from_file(filepath)

            # Verify feature
            feature = config.features[0]
            assert feature.id == "AUTH-001"
            assert feature.metadata is not None
            assert feature.metadata.owner == "auth-team"
            assert feature.metadata.priority == Priority.CRITICAL
            assert len(feature.metadata.external_references) == 1

            # Verify scenario
            scenario = feature.scenarios[0]
            assert scenario.id == "login-success"
            assert scenario.priority == Priority.CRITICAL
            assert scenario.metadata is not None
            assert scenario.metadata.test_type == TestType.SMOKE
            assert "database" in scenario.metadata.dependencies

            # Verify steps
            assert len(scenario.steps) == 3
            assert scenario.steps[1].metadata is not None
            assert scenario.steps[1].metadata.timeout_seconds == 10

            # Verify test data
            assert len(scenario.test_data) == 2
            assert scenario.test_data[0].params["username"] == "user1"
        finally:
            Path(filepath).unlink()

    def test_multiple_features_multiple_scenarios(self) -> None:
        """Test config with multiple features and scenarios."""
        step = TestStep(type=StepType.WHEN, description="action")

        scenarios1 = [
            Scenario(id="s1", name="Scenario 1", steps=[step]),
            Scenario(id="s2", name="Scenario 2", steps=[step]),
        ]
        scenarios2 = [
            Scenario(
                id="s1", name="Scenario 1", steps=[step]
            ),  # Same ID but different feature
            Scenario(id="s3", name="Scenario 3", steps=[step]),
        ]

        feature1 = Feature(id="FEAT-001", name="Feature 1", scenarios=scenarios1)
        feature2 = Feature(id="FEAT-002", name="Feature 2", scenarios=scenarios2)

        config = FeaturesConfig(features=[feature1, feature2])

        assert len(config.features) == 2
        assert len(config.features[0].scenarios) == 2
        assert len(config.features[1].scenarios) == 2

        # Same scenario ID allowed across different features
        assert config.features[0].scenarios[0].id == "s1"
        assert config.features[1].scenarios[0].id == "s1"
