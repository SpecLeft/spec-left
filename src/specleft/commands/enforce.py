"""Enforce command for policy validation and enforcement."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, cast

import click
import yaml
from specleft.specleft_signing.schema import PolicyType, SignedPolicy
from specleft.specleft_signing.verify import VerifyFailure, VerifyResult, verify_policy

from specleft.enforcement.engine import evaluate_policy
from specleft.license.repo_identity import detect_repo_identity


def load_policy(path: str) -> SignedPolicy | None:
    """Load and validate a policy file.

    Args:
        path: Path to policy YAML file

    Returns:
        SignedPolicy if valid, None if loading failed
    """
    try:
        content = yaml.safe_load(Path(path).read_text())
        return SignedPolicy.model_validate(content)
    except FileNotFoundError:
        click.echo(f"Error: Policy file not found: {path}", err=True)
        return None
    except yaml.YAMLError as e:
        click.echo(f"Error: Invalid YAML in policy file: {e}", err=True)
        return None
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        return None


def handle_verification_failure(result: VerifyResult) -> None:
    """Display appropriate error message based on failure type.

    Args:
        result: The verification result
    """
    click.echo(f"Error: {result.message}", err=True)

    if result.failure == VerifyFailure.EVALUATION_EXPIRED:
        click.echo("", err=True)
        click.echo("To continue using SpecLeft enforcement:", err=True)
        click.echo("", err=True)
        click.echo("  Option 1: Purchase Enforce license", err=True)
        click.echo("    https://specleft.dev/enforce", err=True)
        click.echo("", err=True)
        click.echo("  Option 2: Switch to Core Policy", err=True)
        click.echo(
            "    Update your CI to use: specleft enforce .specleft/policy-core.yml",
            err=True,
        )
        click.echo("", err=True)

    elif result.failure == VerifyFailure.EXPIRED:
        click.echo("", err=True)
        click.secho(
            "Renew your license at: https://specleft.dev/enforce", err=True, bold=True
        )

    elif result.failure == VerifyFailure.REPO_MISMATCH:
        click.echo("", err=True)
        click.echo("This policy file is licensed for a different repository.", err=True)
        click.echo(
            "Contact support@specleft.dev if you need to transfer your license.",
            err=True,
        )


def display_policy_status(policy: SignedPolicy) -> None:
    """Display the current policy status.

    Args:
        policy: The active policy
    """
    click.echo("")
    if policy.policy_type == PolicyType.ENFORCE:
        if policy.license.evaluation:
            days = (policy.license.evaluation.ends_at - date.today()).days
            if days >= 11:
                click.echo(
                    f"ℹ Enforce policy running in evaluation mode ({days} days remaining)"
                )
            elif 2 <= days <= 10:
                click.secho(
                    f"⚠ Evaluation ends in {days} days — upgrade or switch to Core",
                    fg="yellow",
                )
                click.echo("  Enforce Policy Info: https://specleft.dev/enforce")
            elif days == 1:
                click.secho(
                    "⚠ Evaluation expires tomorrow — CI will block",
                    fg="yellow",
                )
                click.echo("  Enforce Policy Info: https://specleft.dev/enforce")
        else:
            click.secho("Enforce Policy active", fg="cyan", bold=True)
    else:
        if policy.license.derived_from:
            click.echo("Core Policy (downgraded from Enforce)")
        else:
            click.secho("Core Policy active", fg="cyan", bold=True)
    click.echo()


def display_violations(violations: dict[str, Any]) -> None:
    """Display policy violations in table format.

    Args:
        violations: Dictionary with violation details
    """
    if violations["ignored_features"]:
        click.echo(f"Ignored features: {', '.join(violations['ignored_features'])}")
        click.echo()

    if violations["priority_violations"]:
        click.secho("Priority violations:", fg="red", bold=True)
        click.echo()
        for pv in violations["priority_violations"]:
            click.echo(
                f"  \u2717 {pv['feature_id']}/{pv['scenario_id']} "
                f"({pv['priority']}) - NOT IMPLEMENTED"
            )
        click.echo()

    if violations.get("coverage_violations"):
        click.secho("Coverage violations:", fg="red", bold=True)
        click.echo()
        for cv in violations["coverage_violations"]:
            click.secho(
                f" \u2717 Behaviour test coverage below {cv['threshold']}%", bold=True
            )
            click.echo()
            click.echo(f" Current Behaviour Coverage {cv['actual']}%")
        click.echo()
    if not violations["failed"]:
        click.secho("\u2713 All checks passed", fg="green")

    click.echo()
    click.echo("Documentation: https://specleft.dev/docs/enforce")
    click.echo("Support: https://specleft.dev/contact")


@click.command("enforce")
@click.argument(
    "policy_file",
    type=click.Path(exists=False),
    default=".specleft/licenses/policy.yml",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--ignore-feature-id",
    "ignored",
    multiple=True,
    help="Exclude feature from evaluation (Enforce only, repeatable).",
)
@click.option(
    "--dir",
    "features_dir",
    default="features",
    help="Path to features directory.",
)
@click.option(
    "--tests",
    "test_dir",
    default="tests",
    help="Path to tests directory.",
)
def enforce(
    policy_file: str,
    fmt: str,
    ignored: tuple[str, ...],
    features_dir: str,
    test_dir: str,
) -> None:
    """Enforce policy against the source code.

    Validates the policy signature, checks license status, and
    evaluates policy rules against the current repository state.

    Exit codes:
      0 - Policy satisfied
      1 - Policy violated (scenarios/coverage)
      2 - License issue (signature, expired, repo mismatch)
    """
    from specleft.validator import load_specs_directory

    # Load policy
    policy = load_policy(policy_file)
    if not policy:
        sys.exit(2)

    try:
        features = load_specs_directory(features_dir).features
        if not features:
            sys.exit(2)
    except (FileNotFoundError, ValueError):
        click.secho(
            f"Warning: No feature units found in directory: {features_dir}/. Nothing to enforce.",
            fg="yellow",
            err=True,
        )
        click.echo()
        click.echo("Have you defined your features files correctly?")
        click.echo()
        click.echo("You can list detected features with:")
        click.echo(f"  > specleft features list --dir {features_dir}")
        click.echo("")
        click.echo("Documentation: https://specleft.dev/docs/enforce")
        click.echo("Support: https://specleft.dev/contact")
        sys.exit(2)

    # Reject --ignore-feature-id for Core
    if ignored and policy.policy_type == PolicyType.CORE:
        click.echo(
            "Error: --ignore-feature-id requires Enforce policy",
            err=True,
        )
        sys.exit(1)

    # Verify signature, expiry, evaluation
    result = verify_policy(policy)

    # Check repository binding
    if result.valid:
        # Keep command attribute in sync for tests patching either location
        cast(Any, enforce).detect_repo_identity = detect_repo_identity
        repo = detect_repo_identity()
        if repo is None:
            result = VerifyResult(
                valid=False,
                failure=VerifyFailure.REPO_MISMATCH,
                message="Cannot detect repository. Ensure git remote 'origin' exists.",
            )
        elif not repo.matches(policy.license.licensed_to):
            result = VerifyResult(
                valid=False,
                failure=VerifyFailure.REPO_MISMATCH,
                message=f"License for '{policy.license.licensed_to}', "
                f"current repo is '{repo.canonical}'",
            )

    if not result.valid:
        handle_verification_failure(result)
        sys.exit(2)

    # Show policy status (table format only)
    if fmt == "table":
        display_policy_status(policy)
        click.echo("Checking scenarios...")
        if policy.policy_type == PolicyType.ENFORCE:
            click.echo("Checking coverage...")
        click.echo("")

    # Run enforcement
    violations = evaluate_policy(
        policy=policy,
        ignored_features=list(ignored),
        features_dir=features_dir,
        tests_dir=test_dir,
    )

    if fmt == "json":
        click.echo(json.dumps(violations, indent=2))
    else:
        display_violations(violations)

    sys.exit(0 if not violations["failed"] else 1)


# Expose detect_repo_identity for tests patching specleft.commands.enforce
cast(Any, enforce).detect_repo_identity = detect_repo_identity
