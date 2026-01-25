"""Tests for 'specleft contract' commands."""

from __future__ import annotations

import json

from click.testing import CliRunner
from specleft.cli.main import cli


class TestContractCommand:
    """Tests for 'specleft contract' commands."""

    def test_contract_json_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["contract", "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["contract_version"] == "1.0"
        assert payload["specleft_version"] == "0.2.0"
        assert "guarantees" in payload

    def test_contract_test_json_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["contract", "test", "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["contract_version"] == "1.0"
        assert payload["specleft_version"] == "0.2.0"
        assert payload["passed"] is True
        assert payload["checks"]
