"""Init command."""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path
from typing import cast

import click


def _init_example_content() -> dict[str, str]:
    """Generate single-file example feature using canonical template."""
    return {
        "features/example-feature.md": textwrap.dedent(
            """
            # Feature: Example Feature

            ## Scenarios

            ### Scenario: User logs in successfully
            priority: high

            - Given a registered user with email "user@example.com"
            - When the user submits valid credentials
            - Then the user is redirected to the dashboard
            - And the user sees a welcome message

            ### Scenario: Invalid password rejected
            priority: medium

            - Given a registered user with email "user@example.com"
            - When the user submits an incorrect password
            - Then an error message "Invalid credentials" is displayed
            - And the user remains on the login page

            ---
            confidence: low
            source: example
            assumptions:
              - email/password authentication
              - session-based login
            open_questions:
              - password complexity requirements?
              - maximum login attempts before lockout?
            tags:
              - auth
              - example
            owner: dev-team
            component: identity
            ---
            """
        ).strip()
        + "\n",
    }


def _init_plan(example: bool) -> tuple[list[Path], list[tuple[Path, str]]]:
    directories = [Path("features"), Path("tests"), Path(".specleft")]
    files: list[tuple[Path, str]] = []
    if example:
        for rel_path, content in _init_example_content().items():
            files.append((Path(rel_path), content))
    files.append((Path(".specleft/.gitkeep"), ""))
    return directories, files


def _prompt_init_action(features_dir: Path) -> str:
    click.echo(f"Warning: {features_dir}/ directory already exists")
    click.echo("Options:")
    click.echo("  1. Skip initialization (recommended)")
    click.echo("  2. Merge with existing (add example alongside)")
    click.echo("  3. Cancel")
    choice = click.prompt("Choice", default="1", type=click.Choice(["1", "2", "3"]))
    return cast(str, choice)


def _print_init_dry_run(directories: list[Path], files: list[tuple[Path, str]]) -> None:
    click.echo("Dry run: no files will be created.")
    click.echo("")
    click.echo("Would create:")
    for file_path, _ in files:
        click.echo(f"  - {file_path}")
    for directory in directories:
        click.echo(f"  - {directory}/")
    click.echo("")
    click.echo("Summary:")
    click.echo(f"  {len(files)} files would be created")
    click.echo(f"  {len(directories)} directories would be created")


def _apply_init_plan(
    directories: list[Path], files: list[tuple[Path, str]]
) -> list[Path]:
    created: list[Path] = []
    for directory in directories:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            created.append(directory)
    for file_path, content in files:
        if file_path.exists():
            continue
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        created.append(file_path)
    return created


@click.command("init")
@click.option("--example", is_flag=True, help="Create example feature specs.")
@click.option("--blank", is_flag=True, help="Create empty directory structure only.")
@click.option("--dry-run", is_flag=True, help="Show what would be created.")
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    show_default=True,
    help="Output format: 'table' or 'json'.",
)
def init(example: bool, blank: bool, dry_run: bool, format_type: str) -> None:
    """Initialize SpecLeft project directories and example specs."""
    if example and blank:
        message = "Choose either --example or --blank, not both."
        if format_type == "json":
            payload = {"status": "error", "message": message}
            click.echo(json.dumps(payload, indent=2))
        else:
            click.secho(message, fg="red", err=True)
        sys.exit(1)

    if not example and not blank:
        example = True

    if blank:
        example = False

    features_dir = Path("features")
    if features_dir.exists():
        if format_type == "json":
            payload_cancelled = {
                "status": "cancelled",
                "message": "Initialization cancelled; existing features directory requires confirmation.",
            }
            click.echo(json.dumps(payload_cancelled, indent=2))
            sys.exit(2)
        choice = _prompt_init_action(features_dir)
        if choice == "3":
            click.echo("Cancelled")
            sys.exit(2)
        if choice == "1":
            click.echo("Skipping initialization")
            return

    directories, files = _init_plan(example=example)
    if dry_run:
        if format_type == "json":
            payload_dry_run = {
                "status": "ok",
                "dry_run": True,
                "example": example,
                "would_create": [str(path) for path, _ in files],
                "would_create_directories": [str(path) for path in directories],
                "summary": {
                    "files": len(files),
                    "directories": len(directories),
                },
            }
            click.echo(json.dumps(payload_dry_run, indent=2))
            return
        click.echo(
            "Creating SpecLeft example project..."
            if example
            else "Creating SpecLeft directory structure..."
        )
        click.echo("")
        _print_init_dry_run(directories, files)
        return

    if format_type == "json" and not dry_run:
        payload_error = {
            "status": "error",
            "message": "JSON output requires --dry-run to avoid interactive prompts.",
        }
        click.echo(json.dumps(payload_error, indent=2))
        sys.exit(1)

    click.echo(
        "Creating SpecLeft example project..."
        if example
        else "Creating SpecLeft directory structure..."
    )
    click.echo("")
    created = _apply_init_plan(directories, files)
    for path in created:
        if path.is_dir():
            click.echo(f"✓ Created {path}/")
        else:
            click.echo(f"✓ Created {path}")

    click.echo("")
    if example:
        click.echo("Example project ready!")
        click.echo("")
        click.echo("Next steps:")
        click.echo("  1. Review the example: cat features/example-feature.md")
        click.echo("  2. Generate tests: specleft test skeleton")
        click.echo("  3. Run tests: pytest")
        click.echo("  4. Check status: specleft status")
    else:
        click.echo("Directory structure ready!")
        click.echo("")
        click.echo("Next steps:")
        click.echo("  1. Create your first feature: features/<feature-name>.md")
        click.echo("  2. Add scenarios with Given/When/Then steps")
        click.echo("  3. Generate tests: specleft test skeleton")
