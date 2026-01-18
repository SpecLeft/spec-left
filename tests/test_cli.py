"""Tests for specleft.cli module."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner
from specleft.cli.main import cli, to_snake_case


def _write_file(path: Path, content: str) -> None:
    path.write_text(textwrap.dedent(content).strip())


def _create_feature_specs(
    base_dir: Path,
    *,
    feature_id: str,
    story_id: str,
    scenario_id: str,
    include_test_data: bool = False,
    features_dir_name: str = "features",
) -> Path:
    features_dir = base_dir / features_dir_name
    feature_dir = features_dir / feature_id
    story_dir = feature_dir / story_id
    story_dir.mkdir(parents=True, exist_ok=True)

    scenario_file = story_dir / f"{scenario_id.replace('-', '_')}.md"

    _write_file(
        feature_dir / "_feature.md",
        f"""
        ---
        feature_id: {feature_id}
        priority: high
        tags: [core]
        ---

        # Feature: {feature_id.title()} Feature
        """,
    )

    _write_file(
        story_dir / "_story.md",
        f"""
        ---
        story_id: {story_id}
        tags: [smoke]
        ---

        # Story: {story_id.title()} Story
        """,
    )

    test_data_block = ""
    if include_test_data:
        test_data_block = """
        ## Test Data
        | input | expected | description |
        |-------|----------|-------------|
        | a | A | lowercase a |
        | b | B | lowercase b |
        """

    _write_file(
        scenario_file,
        f"""
        ---
        scenario_id: {scenario_id}
        priority: high
        tags: [smoke]
        execution_time: fast
        ---

        # Scenario: {scenario_id.replace('-', ' ').title()}

        {test_data_block}
        ## Steps
        - **Given** a user exists
        - **When** the user logs in
        - **Then** access is granted
        """,
    )

    return features_dir


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
        assert "0.2.0" in result.output

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

    def test_skeleton_missing_features_dir(self) -> None:
        """Test skeleton command when features directory is missing."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["test", "skeleton"])
            assert result.exit_code == 1
            assert "not found" in result.output

    def test_skeleton_generates_single_file(self) -> None:
        """Test skeleton command with --single-file flag."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            _create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )

            result = runner.invoke(
                cli, ["test", "skeleton", "--single-file"], input="y\n"
            )
            assert result.exit_code == 0
            assert "Create this test file (tests/test_generated.py)?" in result.output
            assert "Created:" in result.output

            generated_file = Path("tests/test_generated.py")
            assert generated_file.exists()

            content = generated_file.read_text()
            assert "from specleft import specleft" in content
            assert 'feature_id="auth"' in content
            assert 'scenario_id="login-success"' in content
            assert "skip=True" in content
            assert "Skeleton test - not yet implemented" in content
            assert "def test_login_success" in content
            assert "with specleft.step('Given a user exists'):" in content
            assert "with specleft.step('When the user logs in'):" in content
            assert "with specleft.step('Then access is granted'):" in content
            assert "assert not True" not in content
            assert "Preview:" in result.output

    def test_skeleton_generates_per_feature(self) -> None:
        """Test skeleton command generates one file per feature."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            _create_feature_specs(
                Path("."),
                feature_id="payments",
                story_id="charge",
                scenario_id="card-charge",
            )

            result = runner.invoke(cli, ["test", "skeleton"], input="y\n")
            assert result.exit_code == 0

            generated_file = Path("tests/payments/test_charge.py")
            assert generated_file.exists()

            content = generated_file.read_text()
            assert "from specleft import specleft" in content
            assert 'feature_id="payments"' in content
            assert 'scenario_id="card-charge"' in content
            assert (
                "Create this test file (tests/payments/test_charge.py)?"
                in result.output
            )

    def test_skeleton_custom_output_dir(self) -> None:
        """Test skeleton command with custom output directory."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            _create_feature_specs(
                Path("."),
                feature_id="inventory",
                story_id="availability",
                scenario_id="check-stock",
            )

            result = runner.invoke(
                cli, ["test", "skeleton", "--output-dir", "custom_tests"], input="y\n"
            )
            assert result.exit_code == 0

            generated_file = Path("custom_tests/inventory/test_availability.py")
            assert generated_file.exists()
            assert (
                "Create this test file (custom_tests/inventory/test_availability.py)?"
                in result.output
            )

    def test_skeleton_custom_features_dir(self) -> None:
        """Test skeleton command with custom features directory."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            features_dir = _create_feature_specs(
                Path("."),
                feature_id="support",
                story_id="tickets",
                scenario_id="open-ticket",
                features_dir_name="specs",
            )

            result = runner.invoke(
                cli, ["test", "skeleton", "-f", str(features_dir)], input="y\n"
            )
            assert result.exit_code == 0
            assert Path("tests/support/test_tickets.py").exists()
            assert (
                "Create this test file (tests/support/test_tickets.py)?"
                in result.output
            )

    def test_skeleton_with_parameterized_tests(self) -> None:
        """Test skeleton command generates parameterized tests correctly."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            _create_feature_specs(
                Path("."),
                feature_id="params",
                story_id="format",
                scenario_id="formatting",
                include_test_data=True,
            )

            result = runner.invoke(
                cli, ["test", "skeleton", "--single-file"], input="y\n"
            )
            assert result.exit_code == 0

            content = Path("tests/test_generated.py").read_text()
            assert "@pytest.mark.parametrize" in content
            assert "input, expected" in content
            assert "'a'" in content
            assert "'A'" in content
            assert "skip=True" in content

    def test_skeleton_invalid_dir(self) -> None:
        """Test skeleton command with invalid features directory."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("features").mkdir()

            result = runner.invoke(cli, ["test", "skeleton"])
            assert result.exit_code == 0
            assert "No specs found" in result.output

    def test_skeleton_invalid_schema(self) -> None:
        """Test skeleton command with invalid spec schema."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            features_dir = Path("features")
            features_dir.mkdir()
            feature_dir = features_dir / "invalid"
            feature_dir.mkdir()
            (feature_dir / "_feature.md").write_text("---\nfeature_id: INVALID\n---")

            result = runner.invoke(cli, ["test", "skeleton"])
            assert result.exit_code == 1
            assert "Error loading" in result.output

    def test_skeleton_shows_next_steps(self) -> None:
        """Test skeleton command shows next steps."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            _create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )

            result = runner.invoke(cli, ["test", "skeleton"], input="n\n")
            assert result.exit_code == 0
            assert "Next steps:" in result.output
            assert "pytest" in result.output
            assert "Create this test file (tests/auth/test_login.py)?" in result.output
            assert "Skipped test creation." in result.output
            assert not Path("tests/auth/test_login.py").exists()

    def test_skeleton_preview_output(self) -> None:
        """Test skeleton command outputs a preview."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            _create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )

            result = runner.invoke(cli, ["test", "skeleton"], input="n\n")
            assert result.exit_code == 0
            assert "File: tests/auth/test_login.py" in result.output
            assert "Scenario IDs: login-success" in result.output
            assert "Steps (first scenario): 3" in result.output
            assert "Status: SKIPPED (not implemented)" in result.output
            assert "Preview:" in result.output

    def test_skeleton_skips_existing_file(self) -> None:
        """Test skeleton command skips existing files."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            _create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )

            first_run = runner.invoke(cli, ["test", "skeleton"], input="y\n")
            assert first_run.exit_code == 0
            generated_file = Path("tests/auth/test_login.py")
            assert generated_file.exists()
            initial_content = generated_file.read_text()

            second_run = runner.invoke(cli, ["test", "skeleton"], input="y\n")
            assert second_run.exit_code == 0
            assert (
                "Skipped existing file: tests/auth/test_login.py" in second_run.output
            )
            assert "No new skeleton tests to generate." in second_run.output
            assert "Create this test file" not in second_run.output
            assert generated_file.read_text() == initial_content

    def test_skeleton_tests_are_skipped_in_pytest(self) -> None:
        """Integration test: verify skeleton tests run as SKIPPED in pytest."""
        import subprocess

        runner = CliRunner()
        with runner.isolated_filesystem():
            _create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
            )

            # Generate skeleton test
            result = runner.invoke(cli, ["test", "skeleton"], input="y\n")
            assert result.exit_code == 0
            generated_file = Path("tests/auth/test_login.py")
            assert generated_file.exists()

            # Run pytest on the generated skeleton
            pytest_result = subprocess.run(
                ["pytest", str(generated_file), "-v"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Verify the test was SKIPPED, not failed
            output = pytest_result.stdout + pytest_result.stderr
            assert "SKIPPED" in output or "skipped" in output.lower()
            assert "FAILED" not in output
            # Pytest exit code 0 means all tests passed/skipped (no failures)
            assert pytest_result.returncode == 0
            # Check for the skip reason (may be truncated in verbose output)
            assert "Skeleton test" in output


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
            _create_feature_specs(
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
            assert "Scenarios: 1" in result.output
            assert "Steps: 3" in result.output

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
            features_dir = _create_feature_specs(
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


class TestFeaturesListCommand:
    """Tests for 'specleft features list' command."""

    def test_features_list_outputs_tree(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            _create_feature_specs(
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
            _create_feature_specs(
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
            _create_feature_specs(
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

    def test_features_stats_with_partial_coverage(self) -> None:
        """Test stats when some scenarios have tests and some don't."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Use the helper to create proper spec structure
            _create_feature_specs(
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
