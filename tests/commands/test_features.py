"""Tests for 'specleft features' commands."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from specleft.cli.main import cli

from tests.helpers.specs import create_feature_specs


class TestFeaturesGroup:
    """Tests for 'features' command group."""

    def test_features_group_help(self) -> None:
        """Test 'features' group help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["features", "--help"])
        assert result.exit_code == 0
        assert "validate" in result.output
        assert "list" in result.output
        assert "stats" in result.output


class TestValidateCommand:
    """Tests for 'specleft features validate' command."""

    def test_validate_valid_dir(self) -> None:
        """Test validate command with valid specs directory."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )

            result = runner.invoke(cli, ["features", "validate"])
            assert result.exit_code == 0
            assert "is valid" in result.output
            assert "Features: 1" in result.output
            assert "Stories: 1" in result.output
            assert "Detected nested feature structure" in result.output
            assert "Scenarios: 1" in result.output
            assert "Steps: 3" in result.output

    def test_validate_json_output(self) -> None:
        """Test validate command JSON output."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )

            result = runner.invoke(cli, ["features", "validate", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["valid"] is True
            assert payload["features"] == 1

    def test_validate_missing_dir(self) -> None:
        """Test validate command when directory is missing."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["features", "validate"])
            assert result.exit_code == 1
            assert "Directory not found" in result.output

    def test_validate_invalid_dir(self) -> None:
        """Test validate command with invalid specs directory."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("features").mkdir()

            result = runner.invoke(cli, ["features", "validate"])
            assert result.exit_code == 1
            assert "Validation failed" in result.output

    def test_validate_custom_dir(self) -> None:
        """Test validate command with custom directory."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            features_dir = create_feature_specs(
                Path("."),
                feature_id="payments",
                story_id="refunds",
                scenario_id="refund",
                features_dir_name="specs",
            )

            result = runner.invoke(
                cli, ["features", "validate", "--dir", str(features_dir)]
            )
            assert result.exit_code == 0
            assert "is valid" in result.output
            assert "Detected nested feature structure" in result.output


class TestFeaturesListCommand:
    """Tests for 'specleft features list' command."""

    def test_features_list_outputs_tree(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )

            result = runner.invoke(cli, ["features", "list"])
            assert result.exit_code == 0
            assert "Features (1):" in result.output
            assert "- auth: Auth Feature" in result.output
            assert "- login: Login Story" in result.output
            assert "- login-success: Login Success" in result.output
            assert "Detected nested feature structure" in result.output

    def test_features_list_json_output(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )

            result = runner.invoke(cli, ["features", "list", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["summary"]["features"] == 1
            feature = payload["features"][0]
            assert feature["feature_id"] == "auth"
            # Canonical feature shape with flattened scenarios
            assert feature["title"] == "Auth Feature"
            assert "confidence" in feature  # nullable
            assert "scenarios" in feature  # flattened from stories
            assert "stories" not in feature  # no stories nesting
            scenario = feature["scenarios"][0]
            assert scenario["id"] == "login-success"  # canonical uses 'id'

    def test_nested_structure_warning(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="legacy",
                story_id="billing",
                scenario_id="legacy-charge",
            )

            result = runner.invoke(cli, ["features", "list"])
            assert result.exit_code == 0
            assert "Detected nested feature structure" in result.output
            assert "features/legacy/_feature.md" not in result.output

    def test_features_list_missing_dir(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["features", "list"])
            assert result.exit_code == 1
            assert "Directory not found" in result.output


class TestFeaturesStatsCommand:
    """Tests for 'specleft features stats' command."""

    def test_features_stats_outputs_summary(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
                include_test_data=True,
            )

            result = runner.invoke(cli, ["features", "stats"])
            assert result.exit_code == 0
            # New format includes test coverage stats
            assert "Test Coverage Stats" in result.output
            assert "Pytest Tests:" in result.output
            assert "Total pytest tests discovered:" in result.output
            assert "Tests with @specleft:" in result.output
            # Specifications section
            assert "Specifications:" in result.output
            assert "Features: 1" in result.output
            assert "Stories: 1" in result.output
            assert "Scenarios: 1" in result.output
            assert "Steps: 3" in result.output
            assert "Parameterized scenarios: 1" in result.output
            assert "Tags:" in result.output
            # Coverage section
            assert "Coverage:" in result.output
            assert "Scenarios with tests:" in result.output
            assert "Scenarios without tests:" in result.output
            assert "Detected nested feature structure" in result.output

    def test_features_stats_json_output(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
                include_test_data=True,
            )

            result = runner.invoke(cli, ["features", "stats", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["specs"]["features"] == 1
            assert payload["coverage"]["scenarios_without_tests"] >= 0

    def test_features_stats_missing_dir(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["features", "stats"])
            assert result.exit_code == 1
            assert "Directory not found" in result.output

    def test_features_stats_with_matching_tests(self) -> None:
        """Test stats when there are tests that match specs."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create spec
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )

            # Create a test file with @specleft decorator matching the spec
            tests_dir = Path("tests")
            tests_dir.mkdir()
            test_file = tests_dir / "test_auth.py"
            test_file.write_text(
                """
from specleft import specleft

@specleft(feature_id="auth", scenario_id="login-success")
def test_login_success():
    pass
"""
            )

            result = runner.invoke(cli, ["features", "stats"])
            assert result.exit_code == 0
            assert "Scenarios with tests: 1" in result.output
            assert "Scenarios without tests: 0" in result.output
            assert "Coverage: 100.0%" in result.output
            assert "Detected nested feature structure" in result.output

    def test_features_stats_with_partial_coverage(self) -> None:
        """Test stats when some scenarios have tests and some don't."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Use the helper to create proper spec structure
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )

            # Add a second scenario manually
            scenario_dir = Path("features/auth/login")
            (scenario_dir / "login-failure.md").write_text(
                """---
scenario_id: login-failure
name: Login Failure
priority: high
---
## Scenario: Login Failure
Given a user exists
When the user logs in with wrong password
Then access is denied
"""
            )

            # Create test file with only one @specleft test
            tests_dir = Path("tests")
            tests_dir.mkdir()
            test_file = tests_dir / "test_auth.py"
            test_file.write_text(
                """
from specleft import specleft

@specleft(feature_id="auth", scenario_id="login-success")
def test_login_success():
    pass
"""
            )

            result = runner.invoke(cli, ["features", "stats"])
            assert result.exit_code == 0
            assert "Scenarios: 2" in result.output
            assert "Scenarios with tests: 1" in result.output
            assert "Scenarios without tests: 1" in result.output
            assert "Coverage: 50.0%" in result.output
            # Should list the uncovered scenario
            assert "login-failure" in result.output
            assert "Detected nested feature structure" in result.output
