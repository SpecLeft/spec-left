"""Tests for specleft.cli module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from specleft.cli.main import cli, to_snake_case


class TestToSnakeCase:
    """Tests for to_snake_case helper function."""

    def test_simple_hyphenated(self) -> None:
        """Test converting hyphenated string."""
        assert to_snake_case("login-success") == "login_success"

    def test_already_snake_case(self) -> None:
        """Test string that's already snake_case."""
        assert to_snake_case("login_success") == "login_success"

    def test_camel_case(self) -> None:
        """Test converting camelCase."""
        assert to_snake_case("loginSuccess") == "login_success"

    def test_with_spaces(self) -> None:
        """Test converting string with spaces."""
        assert to_snake_case("login success") == "login_success"

    def test_mixed_format(self) -> None:
        """Test converting mixed format string."""
        assert to_snake_case("Login-Success Test") == "login_success_test"

    def test_multiple_hyphens(self) -> None:
        """Test handling multiple consecutive hyphens."""
        assert to_snake_case("login--success") == "login_success"


class TestCLIBase:
    """Tests for CLI base commands."""

    def test_cli_version(self) -> None:
        """Test --version flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_help(self) -> None:
        """Test --help flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "SpecLeft" in result.output
        assert "test" in result.output
        assert "features" in result.output


class TestTestGroup:
    """Tests for 'test' command group."""

    def test_test_group_help(self) -> None:
        """Test 'test' group help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["test", "--help"])
        assert result.exit_code == 0
        assert "skeleton" in result.output
        assert "report" in result.output


class TestSkeletonCommand:
    """Tests for 'specleft test skeleton' command."""

    @pytest.fixture
    def sample_features_json(self) -> dict:
        """Sample features.json content for testing."""
        return {
            "version": "1.0",
            "features": [
                {
                    "id": "TEST-001",
                    "name": "Test Feature",
                    "description": "A test feature",
                    "scenarios": [
                        {
                            "id": "scenario-one",
                            "name": "First scenario",
                            "priority": "high",
                            "tags": ["smoke"],
                            "steps": [
                                {"type": "given", "description": "a precondition"},
                                {"type": "when", "description": "an action"},
                                {"type": "then", "description": "a result"},
                            ],
                        },
                    ],
                },
            ],
        }

    @pytest.fixture
    def sample_features_with_test_data(self) -> dict:
        """Sample features.json with parameterized test data."""
        return {
            "version": "1.0",
            "features": [
                {
                    "id": "PARAM-001",
                    "name": "Parameterized Feature",
                    "scenarios": [
                        {
                            "id": "param-scenario",
                            "name": "Parameterized scenario",
                            "priority": "medium",
                            "test_data": [
                                {
                                    "params": {"input": "a", "expected": "A"},
                                    "description": "lowercase a",
                                },
                                {
                                    "params": {"input": "b", "expected": "B"},
                                    "description": "lowercase b",
                                },
                            ],
                            "steps": [
                                {"type": "when", "description": "converting '{input}'"},
                                {
                                    "type": "then",
                                    "description": "result is '{expected}'",
                                },
                            ],
                        },
                    ],
                },
            ],
        }

    def test_skeleton_missing_features_file(self) -> None:
        """Test skeleton command when features.json is missing."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["test", "skeleton"])
            assert result.exit_code == 1
            assert "not found" in result.output

    def test_skeleton_generates_single_file(self, sample_features_json: dict) -> None:
        """Test skeleton command with --single-file flag."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create features.json
            Path("features.json").write_text(json.dumps(sample_features_json))

            # Run skeleton command
            result = runner.invoke(cli, ["test", "skeleton", "--single-file"])
            assert result.exit_code == 0
            assert "Generated" in result.output

            # Check generated file
            generated_file = Path("tests/test_generated.py")
            assert generated_file.exists()

            content = generated_file.read_text()
            assert "from specleft import specleft" in content
            assert (
                '@specleft(feature_id="TEST-001", scenario_id="scenario-one")'
                in content
            )
            assert "def test_scenario_one" in content
            assert 'specleft.step("Given a precondition")' in content
            assert 'specleft.step("When an action")' in content
            assert 'specleft.step("Then a result")' in content

    def test_skeleton_generates_per_feature(self, sample_features_json: dict) -> None:
        """Test skeleton command generates one file per feature."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create features.json
            Path("features.json").write_text(json.dumps(sample_features_json))

            # Run skeleton command (default, no --single-file)
            result = runner.invoke(cli, ["test", "skeleton"])
            assert result.exit_code == 0

            # Check generated file (named after feature ID)
            generated_file = Path("tests/test_test_001.py")
            assert generated_file.exists()

            content = generated_file.read_text()
            assert "from specleft import specleft" in content

    def test_skeleton_custom_output_dir(self, sample_features_json: dict) -> None:
        """Test skeleton command with custom output directory."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create features.json
            Path("features.json").write_text(json.dumps(sample_features_json))

            # Run skeleton command with custom output dir
            result = runner.invoke(
                cli, ["test", "skeleton", "--output-dir", "custom_tests"]
            )
            assert result.exit_code == 0

            # Check file is in custom directory
            assert Path("custom_tests/test_test_001.py").exists()

    def test_skeleton_custom_features_file(self, sample_features_json: dict) -> None:
        """Test skeleton command with custom features file path."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create features file in different location
            Path("config").mkdir()
            Path("config/my_features.json").write_text(json.dumps(sample_features_json))

            # Run skeleton command with custom features file
            result = runner.invoke(
                cli, ["test", "skeleton", "-f", "config/my_features.json"]
            )
            assert result.exit_code == 0
            assert Path("tests/test_test_001.py").exists()

    def test_skeleton_with_parameterized_tests(
        self, sample_features_with_test_data: dict
    ) -> None:
        """Test skeleton command generates parameterized tests correctly."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create features.json
            Path("features.json").write_text(json.dumps(sample_features_with_test_data))

            # Run skeleton command
            result = runner.invoke(cli, ["test", "skeleton", "--single-file"])
            assert result.exit_code == 0

            # Check generated file
            content = Path("tests/test_generated.py").read_text()
            assert "@pytest.mark.parametrize" in content
            assert "input, expected" in content
            assert "'a'" in content
            assert "'A'" in content

    def test_skeleton_invalid_json(self) -> None:
        """Test skeleton command with invalid JSON."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create invalid JSON
            Path("features.json").write_text("{ invalid json }")

            result = runner.invoke(cli, ["test", "skeleton"])
            assert result.exit_code == 1
            assert "Error loading" in result.output

    def test_skeleton_invalid_schema(self) -> None:
        """Test skeleton command with valid JSON but invalid schema."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create JSON with invalid schema (missing required field)
            Path("features.json").write_text(json.dumps({"version": "1.0"}))

            result = runner.invoke(cli, ["test", "skeleton"])
            assert result.exit_code == 1
            assert "Error loading" in result.output

    def test_skeleton_multiple_features(self) -> None:
        """Test skeleton command with multiple features."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            features = {
                "version": "1.0",
                "features": [
                    {
                        "id": "FEAT-A",
                        "name": "Feature A",
                        "scenarios": [
                            {
                                "id": "scenario-a",
                                "name": "Scenario A",
                                "priority": "high",
                                "steps": [
                                    {"type": "given", "description": "something"}
                                ],
                            },
                        ],
                    },
                    {
                        "id": "FEAT-B",
                        "name": "Feature B",
                        "scenarios": [
                            {
                                "id": "scenario-b",
                                "name": "Scenario B",
                                "priority": "medium",
                                "steps": [{"type": "when", "description": "action"}],
                            },
                        ],
                    },
                ],
            }
            Path("features.json").write_text(json.dumps(features))

            result = runner.invoke(cli, ["test", "skeleton"])
            assert result.exit_code == 0

            # Check both files generated
            assert Path("tests/test_feat_a.py").exists()
            assert Path("tests/test_feat_b.py").exists()

    def test_skeleton_shows_next_steps(self, sample_features_json: dict) -> None:
        """Test skeleton command shows next steps."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("features.json").write_text(json.dumps(sample_features_json))

            result = runner.invoke(cli, ["test", "skeleton"])
            assert result.exit_code == 0
            assert "Next steps:" in result.output
            assert "pytest" in result.output


class TestFeaturesGroup:
    """Tests for 'features' command group."""

    def test_features_group_help(self) -> None:
        """Test 'features' group help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["features", "--help"])
        assert result.exit_code == 0
        assert "validate" in result.output


class TestValidateCommand:
    """Tests for 'specleft features validate' command."""

    @pytest.fixture
    def valid_features_json(self) -> dict:
        """Valid features.json for testing."""
        return {
            "version": "1.0",
            "features": [
                {
                    "id": "VALID-001",
                    "name": "Valid Feature",
                    "scenarios": [
                        {
                            "id": "valid-scenario",
                            "name": "Valid Scenario",
                            "priority": "high",
                            "steps": [{"type": "given", "description": "something"}],
                        },
                    ],
                },
            ],
        }

    def test_validate_valid_file(self, valid_features_json: dict) -> None:
        """Test validate command with valid features.json."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("features.json").write_text(json.dumps(valid_features_json))

            result = runner.invoke(cli, ["features", "validate"])
            assert result.exit_code == 0
            assert "is valid" in result.output
            assert "Features: 1" in result.output
            assert "Scenarios: 1" in result.output

    def test_validate_missing_file(self) -> None:
        """Test validate command when file is missing."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["features", "validate"])
            assert result.exit_code == 1
            assert "File not found" in result.output

    def test_validate_invalid_json(self) -> None:
        """Test validate command with invalid JSON."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("features.json").write_text("not valid json")

            result = runner.invoke(cli, ["features", "validate"])
            assert result.exit_code == 1
            assert "Validation failed" in result.output

    def test_validate_invalid_schema(self) -> None:
        """Test validate command with invalid schema."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Invalid feature ID (should be uppercase)
            invalid = {
                "version": "1.0",
                "features": [
                    {
                        "id": "invalid-lowercase",  # Should match ^[A-Z0-9-]+$
                        "name": "Feature",
                        "scenarios": [],
                    },
                ],
            }
            Path("features.json").write_text(json.dumps(invalid))

            result = runner.invoke(cli, ["features", "validate"])
            assert result.exit_code == 1
            assert "Validation failed" in result.output

    def test_validate_custom_file_path(self, valid_features_json: dict) -> None:
        """Test validate command with custom file path."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("config").mkdir()
            Path("config/specs.json").write_text(json.dumps(valid_features_json))

            result = runner.invoke(
                cli, ["features", "validate", "--file", "config/specs.json"]
            )
            assert result.exit_code == 0
            assert "is valid" in result.output


class TestReportCommand:
    """Tests for 'specleft test report' command."""

    @pytest.fixture
    def sample_results(self) -> dict:
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
            # Create results directory and file
            results_dir = Path(".specleft/results")
            results_dir.mkdir(parents=True)
            results_file = results_dir / "results_20250113_100000.json"
            results_file.write_text(json.dumps(sample_results))

            result = runner.invoke(cli, ["test", "report"])
            assert result.exit_code == 0
            assert "Report generated" in result.output

            # Check HTML file exists
            assert Path("report.html").exists()

            # Check HTML content
            content = Path("report.html").read_text()
            assert "SpecLeft Test Report" in content
            assert "TEST-001" in content
            assert "passed" in content.lower()

    def test_report_custom_output(self, sample_results: dict) -> None:
        """Test report command with custom output path."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create results
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
            # Create specific results file
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
            # Create results directory with multiple files
            results_dir = Path(".specleft/results")
            results_dir.mkdir(parents=True)

            # Older file
            (results_dir / "results_20250101_100000.json").write_text(
                json.dumps({**sample_results, "run_id": "old-run"})
            )

            # Newer file
            (results_dir / "results_20250113_100000.json").write_text(
                json.dumps({**sample_results, "run_id": "new-run"})
            )

            result = runner.invoke(cli, ["test", "report"])
            assert result.exit_code == 0

            # Check it used the newer file
            content = Path("report.html").read_text()
            assert "new-run" in content
