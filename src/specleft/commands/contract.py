"""Contract command group."""

from __future__ import annotations

import json
import sys

import click

from specleft.commands.contracts.payloads import (
    build_contract_payload,
    build_contract_test_payload,
)
from specleft.commands.contracts.runner import (
    emit_contract_check,
    run_contract_tests,
)
from specleft.commands.contracts.table import (
    print_contract_table,
    print_contract_test_summary,
)


@click.group(invoke_without_command=True)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    show_default=True,
    help="Output format: 'table' or 'json'.",
)
@click.pass_context
def contract(ctx: click.Context, format_type: str) -> None:
    """Agent contract commands."""
    if ctx.invoked_subcommand is not None:
        return
    payload = build_contract_payload()
    if format_type == "json":
        click.echo(json.dumps(payload, indent=2))
    else:
        print_contract_table(payload)


@contract.command("test")
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    show_default=True,
    help="Output format: 'table' or 'json'.",
)
@click.option("--verbose", is_flag=True, help="Show detailed results for each check.")
def contract_test(format_type: str, verbose: bool) -> None:
    """Verify SpecLeft Agent Contract guarantees."""
    if format_type == "json":
        click.echo("Running contract tests...")
        passed, checks, errors = run_contract_tests(verbose=verbose)
        payload = build_contract_test_payload(
            passed=passed, checks=checks, errors=errors
        )
        click.echo(json.dumps(payload, indent=2))
    else:
        click.echo("SpecLeft Agent Contract Tests")
        click.echo("━" * 44)
        passed, checks, errors = run_contract_tests(
            verbose=verbose,
            on_progress=lambda check: emit_contract_check(check, verbose),
        )
        click.echo("")
        print_contract_test_summary(passed=passed)
        if errors and verbose:
            click.echo("Errors:")
            for error in errors:
                click.echo(f"  - {error}")
    sys.exit(0 if passed else 1)
