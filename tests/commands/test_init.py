"""Tests for 'specleft init' command."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from specleft.cli.main import cli


class TestInitCommand:
    """Tests for 'specleft init' command."""

    def test_init_creates_single_file_example(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init"], input="1\n")
            assert result.exit_code == 0
            assert Path("features/example-feature.md").exists()

    def test_init_json_dry_run(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init", "--dry-run", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["dry_run"] is True
            assert payload["summary"]["directories"] == 3
            assert "features/example-feature.md" in payload["would_create"]

    def test_init_json_requires_dry_run(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init", "--format", "json"])
            assert result.exit_code == 1
            payload = json.loads(result.output)
            assert payload["status"] == "error"

    def test_init_blank_creates_directories(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init", "--blank"])
            assert result.exit_code == 0
            assert Path("features").exists()
            assert Path("tests").exists()
            assert Path(".specleft").exists()
            assert "Directory structure ready" in result.output

    def test_init_example_and_blank_conflict(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init", "--example", "--blank"])
            assert result.exit_code == 1
            assert "Choose either --example or --blank" in result.output

    def test_init_existing_features_skip(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("features").mkdir()
            result = runner.invoke(cli, ["init"], input="1\n")
            assert result.exit_code == 0
            assert "Skipping initialization" in result.output
            assert Path("features").exists()
            assert not Path("tests").exists()

    def test_init_existing_features_merge(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("features").mkdir()
            result = runner.invoke(cli, ["init"], input="2\n")
            assert result.exit_code == 0
            assert Path("features/example-feature.md").exists()

    def test_init_existing_features_cancel(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("features").mkdir()
            result = runner.invoke(cli, ["init"], input="3\n")
            assert result.exit_code == 2
            assert "Cancelled" in result.output
