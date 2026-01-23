"""Tests for 'specleft plan' command."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from specleft.cli.main import cli


class TestPlanCommand:
    """Tests for 'specleft plan' command."""

    def test_plan_missing_prd_warns(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["plan"])
            assert result.exit_code == 0
            assert "PRD not found" in result.output
            assert "Expected locations" in result.output

    def test_plan_creates_features_from_h2(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text("# PRD\n\n## User Authentication\n## Payments\n")
            result = runner.invoke(cli, ["plan"])
            assert result.exit_code == 0
            assert Path("features/user-authentication.md").exists()
            assert Path("features/payments.md").exists()
            assert "Features planned: 2" in result.output

            content = Path("features/user-authentication.md").read_text()
            assert "# Feature: User Authentication" in content
            assert "### Scenario: Example" in content

    def test_plan_uses_h1_when_no_h2(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text("# User Authentication\n")
            result = runner.invoke(cli, ["plan"])
            assert result.exit_code == 0
            assert Path("features/user-authentication.md").exists()
            assert "using top-level title" in result.output

    def test_plan_defaults_to_prd_file_when_no_headings(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text("No headings here")
            result = runner.invoke(cli, ["plan"])
            assert result.exit_code == 0
            assert Path("features/prd.md").exists()
            assert "creating features/prd.md" in result.output

    def test_plan_dry_run_creates_nothing(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text("# User Authentication\n")
            result = runner.invoke(cli, ["plan", "--dry-run"])
            assert result.exit_code == 0
            assert not Path("features").exists()
            assert "Dry run" in result.output
            assert "Would create:" in result.output

    def test_plan_json_output(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text("# User Authentication\n")
            result = runner.invoke(cli, ["plan", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["feature_count"] == 1
            assert payload["created"]

    def test_plan_json_dry_run(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text("# User Authentication\n")
            result = runner.invoke(cli, ["plan", "--format", "json", "--dry-run"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["dry_run"] is True
            assert payload["would_create"]
            assert "created" not in payload

    def test_plan_skips_existing_feature(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            features_dir = Path("features")
            features_dir.mkdir()
            feature_file = features_dir / "user-authentication.md"
            feature_file.write_text("# Feature: User Authentication\n")

            Path("prd.md").write_text("# User Authentication\n")
            result = runner.invoke(cli, ["plan"])
            assert result.exit_code == 0
            assert "Skipped existing" in result.output
            assert feature_file.read_text() == "# Feature: User Authentication\n"
