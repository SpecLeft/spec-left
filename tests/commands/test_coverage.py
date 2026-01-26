"""Tests for 'specleft coverage' command."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from specleft.cli.main import cli

from tests.helpers.specs import create_feature_specs


class TestCoverageCommand:
    """Tests for 'specleft coverage' command."""

    def test_coverage_table_output(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
                scenario_priority="high",
            )
            result = runner.invoke(cli, ["coverage", "--format", "table"])
            assert result.exit_code == 0
            assert "Coverage Report" in result.output
            assert "Overall Coverage" in result.output
            assert "By Feature:" in result.output
            assert "By Priority:" in result.output
            assert "By Execution Time:" in result.output

    def test_coverage_json_output(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
                scenario_priority="critical",
            )
            result = runner.invoke(cli, ["coverage", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert "timestamp" in payload
            coverage = payload["coverage"]
            assert coverage["overall"]["total_scenarios"] == 1
            assert coverage["by_feature"]
            assert coverage["by_priority"]["critical"]["total"] == 1
            assert coverage["by_execution_time"]["fast"]["total"] == 1

    def test_coverage_json_empty_entries(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("features").mkdir()
            Path("features/empty.md").write_text("# Feature: Empty\n\n## Scenarios\n")
            result = runner.invoke(cli, ["coverage", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["coverage"]["overall"]["total_scenarios"] == 0
            assert payload["coverage"]["overall"]["percent"] is None

    def test_coverage_threshold_passes(self) -> None:
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
            result = runner.invoke(
                cli,
                ["coverage", "--format", "json", "--threshold", "90"],
            )
            assert result.exit_code == 0

    def test_coverage_badge_output(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )
            result = runner.invoke(
                cli,
                [
                    "coverage",
                    "--format",
                    "badge",
                    "--output",
                    "coverage.svg",
                ],
            )
            assert result.exit_code == 0
            assert Path("coverage.svg").exists()
            assert "Badge written to" in result.output

    def test_coverage_badge_requires_output(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )
            result = runner.invoke(cli, ["coverage", "--format", "badge"])
            assert result.exit_code == 1
            assert "Badge format requires --output" in result.output

    def test_coverage_threshold_enforced(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )
            result = runner.invoke(
                cli,
                ["coverage", "--format", "json", "--threshold", "90"],
            )
            assert result.exit_code == 1

    def test_coverage_missing_dir(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["coverage", "--format", "json"])
            assert result.exit_code == 1
            assert "Directory not found" in result.output

    def test_coverage_invalid_specs(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("features").mkdir()
            result = runner.invoke(cli, ["coverage", "--format", "json"])
            assert result.exit_code == 1
            assert "Unable to load specs" in result.output
