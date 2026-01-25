"""Integration tests for 'specleft enforce' command.

These tests verify complete workflows from feature specs through enforcement.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner
from specleft.cli.main import cli
from specleft.license.repo_identity import RepoIdentity

from tests.helpers.specs import create_feature_specs
from tests.license.fixtures import (
    TEST_KEY_ID,
    TEST_PUBLIC_KEY_B64,
    add_trusted_key,
    create_core_policy_data,
    create_enforce_policy_data,
    remove_trusted_key,
)


@pytest.fixture(autouse=True)
def setup_test_key():
    """Set up test key for each test."""
    add_trusted_key(TEST_KEY_ID, TEST_PUBLIC_KEY_B64)
    yield
    remove_trusted_key(TEST_KEY_ID)


def write_policy_file(
    base_dir: Path, policy_data: dict, filename: str = "policy.yml"
) -> Path:
    """Write a policy file to .specleft directory."""
    specleft_dir = base_dir / ".specleft"
    specleft_dir.mkdir(parents=True, exist_ok=True)
    policy_path = specleft_dir / filename

    def convert_dates(obj):
        if isinstance(obj, dict):
            return {k: convert_dates(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_dates(item) for item in obj]
        elif isinstance(obj, date):
            return obj.isoformat()
        return obj

    policy_path.write_text(yaml.dump(convert_dates(policy_data)))
    return policy_path


@pytest.mark.integration
class TestEnforceIntegrationWorkflows:
    """Integration tests for complete enforce workflows."""

    def test_workflow_core_pass(self) -> None:
        """features -> skeleton -> implement -> enforce passes."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # 1. Create feature specs with critical scenario
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
                scenario_priority="critical",
            )

            # 2. Create implemented test
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

            # 3. Create Core policy
            policy_data = create_core_policy_data(
                licensed_to="test-owner/test-repo",
                priorities={"critical": {"must_be_implemented": True}},
            )
            write_policy_file(Path("."), policy_data)

            # 4. Mock repo detection and run enforce
            with patch(
                "specleft.commands.enforce.detect_repo_identity",
                return_value=RepoIdentity(owner="test-owner", name="test-repo"),
            ):
                result = runner.invoke(cli, ["enforce", ".specleft/policy.yml"])

            assert result.exit_code == 0
            assert "All checks passed" in result.output

    def test_workflow_core_fail(self) -> None:
        """features -> skeleton -> enforce fails (not implemented)."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # 1. Create feature specs but NO implementation
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
                scenario_priority="critical",
            )

            # 2. Create Core policy requiring critical
            policy_data = create_core_policy_data(
                licensed_to="test-owner/test-repo",
                priorities={"critical": {"must_be_implemented": True}},
            )
            write_policy_file(Path("."), policy_data)

            # 3. Run enforce
            with patch(
                "specleft.commands.enforce.detect_repo_identity",
                return_value=RepoIdentity(owner="test-owner", name="test-repo"),
            ):
                result = runner.invoke(cli, ["enforce", ".specleft/policy.yml"])

            assert result.exit_code == 1
            assert "Priority violations" in result.output
            assert "login-success" in result.output

    def test_workflow_enforce_evaluation(self) -> None:
        """enforce during active evaluation."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
                scenario_priority="critical",
            )

            # Create implemented test
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

            # Create Enforce policy with active evaluation
            today = date.today()
            policy_data = create_enforce_policy_data(
                licensed_to="test-owner/test-repo",
                coverage_threshold=100,
                evaluation_starts=today - timedelta(days=5),
                evaluation_ends=today + timedelta(days=25),
            )
            write_policy_file(Path("."), policy_data)

            with patch(
                "specleft.commands.enforce.detect_repo_identity",
                return_value=RepoIdentity(owner="test-owner", name="test-repo"),
            ):
                result = runner.invoke(cli, ["enforce", ".specleft/policy.yml"])

            assert result.exit_code == 0
            assert "ℹ Enforce policy running in evaluation mode" in result.output
            assert "days remaining" in result.output

    def test_workflow_enforce_purchased(self) -> None:
        """enforce with no evaluation block (purchased license)."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
                scenario_priority="critical",
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

            # Create Enforce policy without evaluation (purchased)
            policy_data = create_enforce_policy_data(
                licensed_to="test-owner/test-repo",
                coverage_threshold=100,
            )
            write_policy_file(Path("."), policy_data)

            with patch(
                "specleft.commands.enforce.detect_repo_identity",
                return_value=RepoIdentity(owner="test-owner", name="test-repo"),
            ):
                result = runner.invoke(cli, ["enforce", ".specleft/policy.yml"])

            assert result.exit_code == 0
            assert "Enforce Policy active" in result.output

    def test_workflow_downgrade_path(self) -> None:
        """eval expires -> switch to policy-core.yml -> works."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
                scenario_priority="critical",
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

            # Expired Enforce policy
            today = date.today()
            enforce_policy = create_enforce_policy_data(
                licensed_to="test-owner/test-repo",
                evaluation_starts=today - timedelta(days=40),
                evaluation_ends=today - timedelta(days=10),
            )
            write_policy_file(Path("."), enforce_policy, "policy.yml")

            # Downgraded Core policy
            core_policy = create_core_policy_data(
                licensed_to="test-owner/test-repo",
                derived_from="lic_test12345678",
                priorities={"critical": {"must_be_implemented": True}},
            )
            write_policy_file(Path("."), core_policy, "policy-core.yml")

            with patch(
                "specleft.commands.enforce.detect_repo_identity",
                return_value=RepoIdentity(owner="test-owner", name="test-repo"),
            ):
                # Enforce policy should fail (expired evaluation)
                result = runner.invoke(cli, ["enforce", ".specleft/policy.yml"])
                assert result.exit_code == 2
                assert "Evaluation" in result.output and "ended" in result.output

                # Core policy should work
                result = runner.invoke(cli, ["enforce", ".specleft/policy-core.yml"])
                assert result.exit_code == 0
                assert "Core Policy (downgraded from Enforce)" in result.output

    def test_workflow_ignore_feature(self) -> None:
        """enforce --ignore-feature-id excludes feature."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create two features
            create_feature_specs(
                Path("."),
                feature_id="auth",
                story_id="login",
                scenario_id="login-success",
                scenario_priority="critical",
            )
            create_feature_specs(
                Path("."),
                feature_id="legacy",
                story_id="old-api",
                scenario_id="legacy-endpoint",
                scenario_priority="critical",
            )

            # Only implement auth
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

            # Enforce policy requiring critical
            policy_data = create_enforce_policy_data(
                licensed_to="test-owner/test-repo",
                coverage_threshold=50,  # Lower threshold to pass
                priorities={"critical": {"must_be_implemented": True}},
            )
            write_policy_file(Path("."), policy_data)

            with patch(
                "specleft.commands.enforce.detect_repo_identity",
                return_value=RepoIdentity(owner="test-owner", name="test-repo"),
            ):
                # Without ignore - should fail (legacy not implemented)
                result = runner.invoke(cli, ["enforce", ".specleft/policy.yml"])
                assert result.exit_code == 1

                # With ignore - should pass
                result = runner.invoke(
                    cli,
                    [
                        "enforce",
                        ".specleft/policy.yml",
                        "--ignore-feature-id",
                        "legacy",
                    ],
                )
                assert result.exit_code == 0
                assert "Ignored features: legacy" in result.output
