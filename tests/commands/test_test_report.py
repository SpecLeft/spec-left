"""Tests for 'specleft test report' command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from specleft.cli.main import cli


@pytest.fixture
def sample_results() -> dict:
    """Sample results JSON for testing."""
    return {
        "run_id": "2025-01-13T10:00:00",
        "summary": {
            "total_features": 1,
            "total_scenarios": 2,
            "total_executions": 3,
            "passed": 2,
            "failed": 1,
            "skipped": 0,
            "duration": 1.234,
        },
        "features": [
            {
                "feature_id": "TEST-001",
                "feature_name": "Test Feature",
                "scenarios": [
                    {
                        "scenario_id": "scenario-one",
                        "scenario_name": "Scenario One",
                        "is_parameterized": False,
                        "executions": [
                            {
                                "test_name": "test_scenario_one",
                                "status": "passed",
                                "duration": 0.5,
                                "steps": [
                                    {
                                        "description": "Given something",
                                        "status": "passed",
                                        "duration": 0.1,
                                    }
                                ],
                            },
                        ],
                        "summary": {
                            "total": 1,
                            "passed": 1,
                            "failed": 0,
                            "skipped": 0,
                        },
                    },
                ],
            },
        ],
    }


class TestReportCommand:
    """Tests for 'specleft test report' command."""

    def test_report_json_output(self, sample_results: dict) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            results_dir = Path(".specleft/results")
            results_dir.mkdir(parents=True)
            results_file = results_dir / "results_20250113_100000.json"
            results_file.write_text(json.dumps(sample_results))

            result = runner.invoke(cli, ["test", "report", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["status"] == "ok"
            assert payload["summary"]["total_features"] == 1

    def test_report_no_results(self) -> None:
        """Test report command when no results exist."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["test", "report"])
            assert result.exit_code == 1
            assert "No results found" in result.output

    def test_report_generates_html(self, sample_results: dict) -> None:
        """Test report command generates HTML file."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            results_dir = Path(".specleft/results")
            results_dir.mkdir(parents=True)
            results_file = results_dir / "results_20250113_100000.json"
            results_file.write_text(json.dumps(sample_results))

            result = runner.invoke(cli, ["test", "report"])
            assert result.exit_code == 0
            assert "Report generated" in result.output

            assert Path("report.html").exists()

            content = Path("report.html").read_text()
            assert "SpecLeft Test Report" in content
            assert "TEST-001" in content
            assert "passed" in content.lower()

    def test_report_custom_output(self, sample_results: dict) -> None:
        """Test report command with custom output path."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            results_dir = Path(".specleft/results")
            results_dir.mkdir(parents=True)
            results_file = results_dir / "results_20250113_100000.json"
            results_file.write_text(json.dumps(sample_results))

            result = runner.invoke(cli, ["test", "report", "-o", "custom_report.html"])
            assert result.exit_code == 0
            assert Path("custom_report.html").exists()

    def test_report_specific_results_file(self, sample_results: dict) -> None:
        """Test report command with specific results file."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("my_results.json").write_text(json.dumps(sample_results))

            result = runner.invoke(cli, ["test", "report", "-r", "my_results.json"])
            assert result.exit_code == 0
            assert Path("report.html").exists()

    def test_report_missing_specific_file(self) -> None:
        """Test report command with non-existent specific results file."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["test", "report", "-r", "nonexistent.json"])
            assert result.exit_code == 1
            assert "not found" in result.output

    def test_report_invalid_json(self) -> None:
        """Test report command with invalid JSON results."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("results.json").write_text("invalid json")

            result = runner.invoke(cli, ["test", "report", "-r", "results.json"])
            assert result.exit_code == 1
            assert "Invalid JSON" in result.output

    def test_report_uses_latest_file(self, sample_results: dict) -> None:
        """Test report command uses the latest results file when multiple exist."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            results_dir = Path(".specleft/results")
            results_dir.mkdir(parents=True)

            (results_dir / "results_20250101_100000.json").write_text(
                json.dumps({**sample_results, "run_id": "old-run"})
            )

            (results_dir / "results_20250113_100000.json").write_text(
                json.dumps({**sample_results, "run_id": "new-run"})
            )

            result = runner.invoke(cli, ["test", "report"])
            assert result.exit_code == 0

            content = Path("report.html").read_text()
            assert "new-run" in content
