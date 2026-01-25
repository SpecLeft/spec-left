"""Tests for 'specleft test skeleton' command."""

from __future__ import annotations

import subprocess
from pathlib import Path

from click.testing import CliRunner
from specleft.cli.main import cli

from tests.helpers.specs import create_feature_specs, create_single_file_feature_spec


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
            create_single_file_feature_spec(
                Path("."),
                feature_id="auth",
                scenario_id="login-success",
            )

            result = runner.invoke(
                cli, ["test", "skeleton", "--single-file"], input="y\n"
            )
            assert result.exit_code == 0
            assert "Confirm creation?" in result.output
            assert "✓ Created 1 test files" in result.output

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

    def test_skeleton_auto_detects_single_file_layout(self) -> None:
        """Test skeleton command auto-detects single-file layout."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_single_file_feature_spec(
                Path("."),
                feature_id="payments",
                scenario_id="card-charge",
            )

            result = runner.invoke(cli, ["test", "skeleton"], input="y\n")
            assert result.exit_code == 0
            assert "Confirm creation?" in result.output
            assert "✓ Created 1 test files" in result.output

            generated_file = Path("tests/test_payments.py")
            assert generated_file.exists()

            content = generated_file.read_text()
            assert "from specleft import specleft" in content
            assert 'feature_id="payments"' in content
            assert 'scenario_id="card-charge"' in content

    def test_skeleton_auto_detects_nested_layout(self) -> None:
        """Test skeleton command auto-detects nested layout."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="legacy",
                story_id="billing",
                scenario_id="legacy-charge",
            )

            result = runner.invoke(cli, ["test", "skeleton"], input="y\n")
            assert result.exit_code == 0
            assert "Confirm creation?" in result.output
            assert "✓ Created 1 test files" in result.output

            generated_file = Path("tests/legacy/test_billing.py")
            assert generated_file.exists()

    def test_skeleton_custom_output_dir(self) -> None:
        """Test skeleton command with custom output directory (single-file layout)."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_single_file_feature_spec(
                Path("."),
                feature_id="inventory",
                scenario_id="check-stock",
            )

            result = runner.invoke(
                cli, ["test", "skeleton", "--output-dir", "custom_tests"], input="y\n"
            )
            assert result.exit_code == 0
            assert "Confirm creation?" in result.output
            assert "✓ Created 1 test files" in result.output

            generated_file = Path("custom_tests/test_inventory.py")
            assert generated_file.exists()

    def test_skeleton_custom_features_dir(self) -> None:
        """Test skeleton command with custom features directory (single-file layout)."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            features_dir = create_single_file_feature_spec(
                Path("."),
                feature_id="support",
                scenario_id="open-ticket",
                features_dir_name="specs",
            )

            result = runner.invoke(
                cli, ["test", "skeleton", "-f", str(features_dir)], input="y\n"
            )
            assert result.exit_code == 0
            assert "Confirm creation?" in result.output
            assert "✓ Created 1 test files" in result.output
            assert Path("tests/test_support.py").exists()

    def test_skeleton_with_parameterized_tests(self) -> None:
        """Test skeleton command generates parameterized tests correctly."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
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
            assert "Confirm creation?" in result.output
            assert "✓ Created 1 test files" in result.output

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

    def test_skeleton_dedupes_duplicate_scenario_ids(self) -> None:
        """Test duplicate scenario names are de-duped with warnings."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_single_file_feature_spec(
                Path("."),
                feature_id="auth",
                scenario_id="example",
            )
            create_single_file_feature_spec(
                Path("."),
                feature_id="billing",
                scenario_id="example",
            )

            result = runner.invoke(cli, ["test", "skeleton"], input="n\n")
            assert result.exit_code == 2
            assert "Duplicate scenario name found" in result.output
            assert "Scenario IDs:" in result.output
            assert "example" in result.output
            assert "example-1" in result.output

    def test_skeleton_dedupes_without_warning_elsewhere(self) -> None:
        """Test duplicate warnings only appear during skeleton command."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_single_file_feature_spec(
                Path("."),
                feature_id="auth",
                scenario_id="example",
            )
            create_single_file_feature_spec(
                Path("."),
                feature_id="billing",
                scenario_id="example",
            )

            result = runner.invoke(cli, ["features", "list"])
            assert result.exit_code == 0
            assert "Duplicate scenario name found" not in result.output

    def test_skeleton_shows_next_steps(self) -> None:
        """Test skeleton command shows next steps."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_single_file_feature_spec(
                Path("."),
                feature_id="auth",
                scenario_id="login-success",
            )

            result = runner.invoke(cli, ["test", "skeleton"], input="n\n")
            assert result.exit_code == 2
            assert "Confirm creation?" in result.output
            assert "Cancelled" in result.output
            assert not Path("tests/test_auth.py").exists()

    def test_skeleton_preview_output(self) -> None:
        """Test skeleton command outputs a preview."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_single_file_feature_spec(
                Path("."),
                feature_id="auth",
                scenario_id="login-success",
            )

            result = runner.invoke(cli, ["test", "skeleton"], input="n\n")
            assert result.exit_code == 2
            assert "File: tests/test_auth.py" in result.output
            assert "Scenario IDs: login-success" in result.output
            assert "Steps (first scenario): 3" in result.output
            assert "Status: SKIPPED (not implemented)" in result.output
            assert "Preview:" in result.output
            assert "Confirm creation?" in result.output
            assert "Cancelled" in result.output

    def test_skeleton_skips_existing_file(self) -> None:
        """Test skeleton command skips existing files."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_single_file_feature_spec(
                Path("."),
                feature_id="auth",
                scenario_id="login-success",
            )

            first_run = runner.invoke(cli, ["test", "skeleton"], input="y\n")
            assert first_run.exit_code == 0
            generated_file = Path("tests/test_auth.py")
            assert generated_file.exists()
            initial_content = generated_file.read_text()

            second_run = runner.invoke(cli, ["test", "skeleton"], input="y\n")
            assert second_run.exit_code == 0
            assert "No new skeleton tests to generate." in second_run.output
            assert generated_file.read_text() == initial_content

    def test_skeleton_tests_are_skipped_in_pytest(self) -> None:
        """Integration test: verify skeleton tests run as SKIPPED in pytest."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_single_file_feature_spec(
                Path("."),
                feature_id="auth",
                scenario_id="login-success",
            )

            # Generate skeleton test
            result = runner.invoke(cli, ["test", "skeleton"], input="y\n")
            assert result.exit_code == 0
            assert "Confirm creation?" in result.output
            assert "✓ Created 1 test files" in result.output
            generated_file = Path("tests/test_auth.py")
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
            assert "FAILED" not in output
            # Pytest exit code 0 means all tests passed/skipped (no failures)
            assert pytest_result.returncode == 0
            # Check for the skip reason (may be truncated in verbose output)
            assert "Skeleton test" in output
