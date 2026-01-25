"""Tests for 'specleft doctor' command."""

from __future__ import annotations

import json

from click.testing import CliRunner
from specleft.cli.main import cli


class TestDoctorCommand:
    """Tests for 'specleft doctor' command."""

    def test_doctor_json_includes_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor", "--format", "json"])
        assert result.exit_code in {0, 1}
        payload = json.loads(result.output)
        assert payload["version"] == "0.2.0"
        assert "healthy" in payload
        assert "checks" in payload

    def test_doctor_table_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code in {0, 1}
        assert "Checking SpecLeft installation" in result.output
        assert "specleft CLI available" in result.output

    def test_doctor_verbose_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor", "--verbose"])
        assert result.exit_code in {0, 1}
        assert "pytest plugin" in result.output
