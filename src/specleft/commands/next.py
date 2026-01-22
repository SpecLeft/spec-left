"""Next command."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import click

from specleft.commands.formatters import get_priority_value
from specleft.commands.status import build_status_entries
from specleft.commands.types import ScenarioStatusEntry, StatusSummary
from specleft.utils.structure import warn_if_nested_structure


def _priority_sort_value(priority: str) -> int:
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return order.get(priority, 4)


def _summarize_status_entries(entries: list[ScenarioStatusEntry]) -> StatusSummary:
    total_scenarios = len(entries)
    implemented = sum(1 for entry in entries if entry.status == "implemented")
    skipped = total_scenarios - implemented
    total_features = len({entry.feature.feature_id for entry in entries})
    total_stories = len(
        {(entry.feature.feature_id, entry.story.story_id) for entry in entries}
    )
    coverage_percent = int(
        round((implemented / total_scenarios * 100) if total_scenarios else 0)
    )

    return StatusSummary(
        total_features=total_features,
        total_stories=total_stories,
        total_scenarios=total_scenarios,
        implemented=implemented,
        skipped=skipped,
        coverage_percent=coverage_percent,
    )


def _print_next_table(
    entries: list[ScenarioStatusEntry], summary: StatusSummary
) -> None:
    if not entries:
        click.echo("All scenarios are implemented! 🎉")
        click.echo("")
        click.echo(f"Total scenarios: {summary.total_scenarios}")
        click.echo(f"Implemented: {summary.implemented}")
        click.echo(f"Coverage: {summary.coverage_percent}%")
        return

    click.echo("")
    click.secho("Next Tests", fg="cyan", bold=True)
    click.echo("")
    for entry in entries:
        click.echo(
            f"- {entry.feature.feature_id}/{entry.story.story_id}/{entry.scenario.scenario_id}"
        )
        click.echo(f"  Priority: {get_priority_value(entry.scenario)}")
        click.echo(
            f"  Tags: {', '.join(entry.scenario.tags) if entry.scenario.tags else 'none'}"
        )
        click.echo(f"  Test: {entry.test_file}::{entry.test_function}")
        click.echo("")

    click.echo(f"Showing {len(entries)} of {summary.total_scenarios} scenarios")


def _build_next_json(
    entries: list[ScenarioStatusEntry], total_unimplemented: int
) -> dict[str, Any]:
    tests: list[dict[str, Any]] = []
    for entry in entries:
        payload: dict[str, Any] = {
            "feature_id": entry.feature.feature_id,
            "feature_name": entry.feature.name,
            "story_id": entry.story.story_id,
            "story_name": entry.story.name,
            "scenario_id": entry.scenario.scenario_id,
            "scenario_name": entry.scenario.name,
            "priority": get_priority_value(entry.scenario),
            "tags": entry.scenario.tags,
            "spec_file": (
                str(entry.scenario.source_file) if entry.scenario.source_file else None
            ),
            "test_file": entry.test_file,
            "test_function": entry.test_function,
            "steps": [
                {"type": step.type.value, "description": step.description}
                for step in entry.scenario.steps
            ],
            "step_count": len(entry.scenario.steps),
        }
        tests.append(payload)

    output = {
        "timestamp": datetime.now().isoformat(),
        "tests": tests,
        "total_unimplemented": total_unimplemented,
        "showing": len(tests),
    }
    if not tests:
        output["message"] = "All scenarios are implemented"
    return output


@click.command("next")
@click.option(
    "--dir",
    "features_dir",
    default="features",
    help="Path to features directory.",
)
@click.option(
    "--limit",
    default=5,
    show_default=True,
    type=int,
    help="Number of tests to show.",
)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    show_default=True,
    help="Output format: 'table' or 'json'.",
)
@click.option(
    "--priority",
    "priority_filter",
    type=click.Choice(["critical", "high", "medium", "low"], case_sensitive=False),
    help="Filter by priority.",
)
@click.option("--feature", "feature_id", help="Filter by feature ID.")
@click.option("--story", "story_id", help="Filter by story ID.")
def next_command(
    features_dir: str,
    limit: int,
    format_type: str,
    priority_filter: str | None,
    feature_id: str | None,
    story_id: str | None,
) -> None:
    """Show the next tests to implement."""
    from specleft.validator import load_specs_directory

    try:
        config = load_specs_directory(features_dir)
    except FileNotFoundError:
        click.secho(f"Directory not found: {features_dir}", fg="red", err=True)
        sys.exit(1)
    except ValueError as exc:
        click.secho(f"Unable to load specs: {exc}", fg="red", err=True)
        sys.exit(1)

    # Gentle nudge for nested structures (table output only)
    if format_type == "table":
        warn_if_nested_structure(Path(features_dir))

    entries = build_status_entries(
        config,
        Path("tests"),
        feature_id=feature_id,
        story_id=story_id,
    )

    summary = _summarize_status_entries(entries)
    unimplemented = [entry for entry in entries if entry.status == "skipped"]
    if priority_filter:
        unimplemented = [
            entry
            for entry in unimplemented
            if get_priority_value(entry.scenario) == priority_filter
        ]

    unimplemented.sort(
        key=lambda entry: (
            _priority_sort_value(get_priority_value(entry.scenario)),
            entry.feature.feature_id,
            entry.story.story_id,
            entry.scenario.scenario_id,
        )
    )

    limited = unimplemented[: max(limit, 0)]
    if format_type == "json":
        payload = _build_next_json(limited, len(unimplemented))
        click.echo(json.dumps(payload, indent=2))
    else:
        _print_next_table(limited, summary)
