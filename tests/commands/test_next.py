"""Tests for 'specleft next' command."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from specleft.cli.main import cli

from tests.helpers.specs import create_feature_specs


class TestNextCommand:
    """Tests for 'specleft next' command."""

    def test_next_json_output(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )
            result = runner.invoke(cli, ["next", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["showing"] == 1

    def test_next_json_omits_execution_time(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
                execution_time="slow",
            )
            result = runner.invoke(cli, ["next", "--format", "json"])
            payload = json.loads(result.output)
            scenario = payload["tests"][0]
            assert "execution_time" not in scenario

    def test_next_respects_priority_and_limit(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
                scenario_priority="low",
            )
            create_feature_specs(
                Path("."),
                feature_id="payments",
                story_id="refunds",
                scenario_id="issue-refund",
                scenario_priority="critical",
            )
            result = runner.invoke(cli, ["next", "--format", "json", "--limit", "1"])
            payload = json.loads(result.output)
            assert payload["showing"] == 1
            assert payload["tests"][0]["scenario_id"] == "issue-refund"

    def test_next_filters_by_priority(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
                scenario_priority="high",
            )
            create_feature_specs(
                Path("."),
                feature_id="payments",
                story_id="refunds",
                scenario_id="issue-refund",
                scenario_priority="low",
            )
            result = runner.invoke(
                cli, ["next", "--format", "json", "--priority", "high"]
            )
            payload = json.loads(result.output)
            assert payload["showing"] == 1
            assert payload["tests"][0]["scenario_id"] == "login-success"

    def test_next_outputs_success_when_all_implemented(self) -> None:
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
            result = runner.invoke(cli, ["next"])
            assert result.exit_code == 0
            assert "All scenarios are implemented" in result.output
