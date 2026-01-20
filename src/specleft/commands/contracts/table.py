"""Table output for contract commands."""

from __future__ import annotations

from typing import Any

import click

from specleft.commands.constants import CONTRACT_DOC_PATH
from specleft.commands.contracts.types import ContractCheckResult


def print_contract_table(payload: dict[str, object]) -> None:
    guarantees = payload.get("guarantees", {})
    safety = guarantees.get("safety", {})
    execution = guarantees.get("execution", {})
    determinism = guarantees.get("determinism", {})
    cli_api = guarantees.get("cli_api", {})
    click.echo("SpecLeft Agent Contract")
    click.echo("─" * 40)
    click.echo(f"Contract version: {payload.get('contract_version')}")
    click.echo(f"SpecLeft version: {payload.get('specleft_version')}")
    click.echo("")
    click.echo("Safety:")
    click.echo(
        "  - No writes without confirmation or --force"
        if safety.get("no_implicit_writes")
        else "  - No implicit writes guarantee missing"
    )
    click.echo(
        "  - --dry-run never writes to disk"
        if safety.get("dry_run_no_writes")
        else "  - --dry-run guarantee missing"
    )
    click.echo(
        "  - Existing tests not modified by default"
        if safety.get("existing_tests_not_modified_by_default")
        else "  - Existing test protection missing"
    )
    click.echo("")
    click.echo("Execution:")
    click.echo(
        "  - Skeleton tests skipped by default"
        if execution.get("skeletons_skipped_by_default")
        else "  - Skeleton skip guarantee missing"
    )
    click.echo(
        "  - Skipped scenarios never fail tests"
        if execution.get("skipped_never_fail")
        else "  - Skip behavior guarantee missing"
    )
    click.echo(
        "  - Validation is non-destructive"
        if execution.get("validation_non_destructive")
        else "  - Validation guarantee missing"
    )
    click.echo("")
    click.echo("Determinism:")
    click.echo(
        "  - Commands deterministic for same inputs"
        if determinism.get("deterministic_for_same_inputs")
        else "  - Determinism guarantee missing"
    )
    click.echo(
        "  - Safe to re-run in retry loops"
        if determinism.get("safe_for_retries")
        else "  - Retry safety guarantee missing"
    )
    click.echo("")
    click.echo("JSON & CLI:")
    click.echo(
        "  - All commands support --format json"
        if cli_api.get("json_supported_globally")
        else "  - JSON support guarantee missing"
    )
    click.echo(
        "  - JSON schema additive within minor versions"
        if cli_api.get("json_additive_within_minor")
        else "  - JSON compatibility guarantee missing"
    )
    click.echo("  - Stable exit codes: 0=success, 1=error, 2=cancel")
    click.echo("")
    click.echo(f"For full details, see: {CONTRACT_DOC_PATH}")
    click.echo("─" * 40)


def format_contract_check_label(check: ContractCheckResult) -> str:
    return f"{check.category.capitalize()}: {check.name.replace('_', ' ')}"


def emit_contract_check(check: ContractCheckResult, verbose: bool) -> None:
    marker = "✓" if check.status == "pass" else "✗"
    click.echo(f"{marker} {format_contract_check_label(check)}")
    if verbose and check.message:
        click.echo(f"  {check.message}")


def print_contract_test_summary(*, passed: bool) -> None:
    if passed:
        click.echo("All Agent Contract guarantees verified.")
    else:
        click.echo("One or more Agent Contract guarantees failed.")
