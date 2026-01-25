"""Tests for 'specleft status' command."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from specleft.cli.main import cli

from tests.helpers.specs import create_feature_specs, create_single_file_feature_spec


class TestStatusCommand:
    """Tests for 'specleft status' command."""

    def test_status_json_includes_execution_time(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
                execution_time="slow",
            )
            result = runner.invoke(cli, ["status", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            scenarios = payload["features"][0]["scenarios"]
            assert scenarios[0]["execution_time"] == "slow"

    def test_status_groups_by_feature_file(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_single_file_feature_spec(
                Path("."),
                feature_id="auth",
                scenario_id="login-success",
            )
            result = runner.invoke(cli, ["status"])
            assert result.exit_code == 0
            assert "Feature File: features/auth.md" in result.output
            assert "login-success" in result.output

    def test_status_unimplemented_table_output(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )
            result = runner.invoke(cli, ["status", "--unimplemented"])
            assert result.exit_code == 0
            assert "Unimplemented Scenarios" in result.output
            assert "⚠ auth/login/login-success" in result.output
            assert "Detected nested feature structure" in result.output

    def test_status_filter_requires_valid_ids(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )
            result = runner.invoke(cli, ["status", "--feature", "missing"])
            assert result.exit_code == 1
            assert "Unknown feature ID" in result.output

    def test_status_treats_missing_test_file_as_skipped(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )
            result = runner.invoke(cli, ["status", "--format", "json"])
            payload = json.loads(result.output)
            scenario = payload["features"][0]["scenarios"][0]
            assert scenario["status"] == "skipped"
            assert "test_login.py" in scenario["test_file"]  # nested layout default

    def test_status_marks_skipped_when_decorator_skip_true(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )
            tests_dir = Path("tests") / "auth"
            tests_dir.mkdir(parents=True)
            (tests_dir / "test_login.py").write_text(
                """
from specleft import specleft

@specleft(feature_id="auth", scenario_id="login-success", skip=True)
def test_login_success():
    pass
"""
            )

            result = runner.invoke(cli, ["status", "--format", "json"])
            scenario = json.loads(result.output)["features"][0]["scenarios"][0]
            assert scenario["status"] == "skipped"
            assert scenario["reason"] == "Not implemented"

    def test_status_marks_implemented_when_skip_removed(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )
            tests_dir = Path("tests") / "auth"
            tests_dir.mkdir(parents=True)
            (tests_dir / "test_login.py").write_text(
                """
from specleft import specleft

@specleft(feature_id="auth", scenario_id="login-success")
def test_login_success():
    pass
"""
            )

            result = runner.invoke(cli, ["status", "--format", "json"])
            scenario = json.loads(result.output)["features"][0]["scenarios"][0]
            assert scenario["status"] == "implemented"

    def test_status_json_canonical_shape(self) -> None:
        """Test status JSON output matches canonical feature shape."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )
            result = runner.invoke(cli, ["status", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)

            feature = payload["features"][0]
            # Canonical feature fields
            assert feature["feature_id"] == "auth"
            assert feature["title"] == "Auth Feature"
            assert "confidence" in feature  # nullable
            assert "source" in feature  # nullable
            assert "assumptions" in feature  # nullable
            assert "open_questions" in feature  # nullable
            assert "owner" in feature  # nullable
            assert "component" in feature  # nullable
            assert "tags" in feature

            # Scenarios flattened (no stories nesting)
            assert "scenarios" in feature
            assert "stories" not in feature
            scenario = feature["scenarios"][0]
            assert (
                scenario["id"] == "login-success"
            )  # canonical uses 'id' not 'scenario_id'
            assert scenario["title"] == "Login Success"
            assert "priority" in scenario
            assert "tags" in scenario
            assert "steps" in scenario
