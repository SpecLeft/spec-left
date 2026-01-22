"""Status command helpers."""

from __future__ import annotations

import ast
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import click

from specleft.commands.formatters import get_priority_value
from specleft.commands.types import ScenarioStatus, ScenarioStatusEntry, StatusSummary
from specleft.schema import SpecsConfig
from specleft.utils.structure import warn_if_nested_structure
from specleft.utils.test_discovery import extract_specleft_calls


def _iter_py_files(tests_dir: Path) -> list[Path]:
    if not tests_dir.exists():
        return []

    return [
        file_path
        for file_path in tests_dir.rglob("*.py")
        if not file_path.name.startswith("__")
    ]


def _index_specleft_tests(tests_dir: Path) -> dict[str, dict[str, object]]:
    scenario_map: dict[str, dict[str, object]] = {}
    for file_path in _iter_py_files(tests_dir):
        try:
            content = file_path.read_text()
        except OSError:
            continue

        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue

        for scenario_id, info in extract_specleft_calls(tree).items():
            scenario_map[scenario_id] = {
                "function": info["function"],
                "skip": info["skip"],
                "file": str(file_path),
            }

    return scenario_map


def _build_status_table_rows(entries: list[ScenarioStatusEntry]) -> list[str]:
    if not entries:
        return []

    max_path_len = max(
        len(f"{entry.test_file}::{entry.test_function}") for entry in entries
    )
    width = max(70, max_path_len + 10)
    return ["━" * width]


def _determine_scenario_status(
    *,
    test_file_path: str,
    test_info: dict[str, object] | None,
) -> ScenarioStatus:
    test_path = Path(test_file_path)
    if test_info is None:
        reason = "Test file not created"
        if test_path.exists():
            reason = "Test decorator not found"
        return ScenarioStatus(
            status="skipped",
            test_file=test_file_path,
            test_function=None,
            reason=reason,
        )

    if bool(test_info.get("skip")):
        return ScenarioStatus(
            status="skipped",
            test_file=str(test_info.get("file")),
            test_function=str(test_info.get("function")),
            reason="Not implemented",
        )

    return ScenarioStatus(
        status="implemented",
        test_file=str(test_info.get("file")),
        test_function=str(test_info.get("function")),
        reason=None,
    )


def build_status_entries(
    config: SpecsConfig,
    tests_dir: Path,
    *,
    feature_id: str | None = None,
    story_id: str | None = None,
) -> list[ScenarioStatusEntry]:
    scenario_map = _index_specleft_tests(tests_dir)
    entries: list[ScenarioStatusEntry] = []

    for feature in config.features:
        if feature_id and feature.feature_id != feature_id:
            continue

        for story in feature.stories:
            if story_id and story.story_id != story_id:
                continue

            if _is_single_file_feature(feature):
                test_file = _feature_output_path(tests_dir, feature.feature_id)
            else:
                test_file = _story_output_path(
                    tests_dir, feature.feature_id, story.story_id
                )

            for scenario in story.scenarios:
                info = scenario_map.get(scenario.scenario_id)
                status = _determine_scenario_status(
                    test_file_path=str(test_file),
                    test_info=info,
                )
                entries.append(
                    ScenarioStatusEntry(
                        feature=feature,
                        story=story,
                        scenario=scenario,
                        status=status.status,
                        test_file=status.test_file or str(test_file),
                        test_function=status.test_function
                        or scenario.test_function_name,
                        reason=status.reason,
                    )
                )

    return entries


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


def build_status_json(
    entries: list[ScenarioStatusEntry],
    *,
    include_execution_time: bool,
) -> dict[str, Any]:
    from specleft.commands.formatters import build_feature_json

    summary = _summarize_status_entries(entries)
    features: list[dict[str, Any]] = []

    feature_groups: dict[str, list[ScenarioStatusEntry]] = {}
    for entry in entries:
        feature_groups.setdefault(entry.feature.feature_id, []).append(entry)

    for feature_entries in feature_groups.values():
        feature_summary = _summarize_status_entries(feature_entries)
        feature = feature_entries[0].feature

        # Build scenario status info to merge into canonical JSON
        scenario_status: dict[str, dict[str, Any]] = {}
        for entry in feature_entries:
            status_info: dict[str, Any] = {
                "status": entry.status,
                "test_file": entry.test_file,
                "test_function": entry.test_function,
            }
            if include_execution_time:
                status_info["execution_time"] = entry.scenario.execution_time.value
            if entry.reason:
                status_info["reason"] = entry.reason
            scenario_status[entry.scenario.scenario_id] = status_info

        # Get all scenarios from entries (flattened from stories)
        scenarios = [entry.scenario for entry in feature_entries]

        # Use canonical builder with status info
        feature_payload = build_feature_json(
            feature,
            scenarios=scenarios,
            include_status=scenario_status,
        )

        # Add status-specific fields
        feature_payload["feature_file"] = (
            str(feature.source_file)
            if feature.source_file
            else (
                str(feature.source_dir / "_feature.md") if feature.source_dir else None
            )
        )
        feature_payload["coverage_percent"] = feature_summary.coverage_percent
        feature_payload["summary"] = {
            "total_scenarios": feature_summary.total_scenarios,
            "implemented": feature_summary.implemented,
            "skipped": feature_summary.skipped,
        }

        features.append(feature_payload)

    return {
        "timestamp": datetime.now().isoformat(),
        "features": features,
        "summary": {
            "total_features": summary.total_features,
            "total_stories": summary.total_stories,
            "total_scenarios": summary.total_scenarios,
            "implemented": summary.implemented,
            "skipped": summary.skipped,
            "coverage_percent": summary.coverage_percent,
        },
    }


def print_status_table(
    entries: list[ScenarioStatusEntry],
    *,
    show_only: str | None = None,
) -> None:
    summary = _summarize_status_entries(entries)
    if not entries:
        click.echo("No scenarios found.")
        return

    if show_only == "unimplemented":
        click.echo(f"Unimplemented Scenarios ({summary.skipped})")
        separator = _build_status_table_rows(entries)
        if separator:
            click.echo(separator[0])
        for entry in entries:
            if entry.status != "skipped":
                continue
            path = f"{entry.feature.feature_id}/{entry.story.story_id}/{entry.scenario.scenario_id}"
            click.echo(f"⚠ {path}")
            click.echo(f"  → {entry.test_file}::{entry.test_function}")
            click.echo(
                f"  Priority: {get_priority_value(entry.scenario)} | Tags: {', '.join(entry.scenario.tags) if entry.scenario.tags else 'none'}"
            )
            if entry.reason:
                click.echo(f"  Reason: {entry.reason}")
            click.echo("")

        if separator:
            click.echo(separator[0])
        return

    if show_only == "implemented":
        click.echo(f"Implemented Scenarios ({summary.implemented})")
        separator = _build_status_table_rows(entries)
        if separator:
            click.echo(separator[0])
        for entry in entries:
            if entry.status != "implemented":
                continue
            path = f"{entry.feature.feature_id}/{entry.story.story_id}/{entry.scenario.scenario_id}"
            click.echo(f"✓ {path}")
            click.echo(f"  → {entry.test_file}::{entry.test_function}")
            click.echo("")

        if separator:
            click.echo(separator[0])
        return

    click.echo("Feature Coverage Report")
    separator = _build_status_table_rows(entries)
    if separator:
        click.echo(separator[0])

    # Group by feature file for Phase 4 compliance
    feature_groups: dict[str, list[ScenarioStatusEntry]] = {}
    for entry in entries:
        feature_groups.setdefault(entry.feature.feature_id, []).append(entry)

    for feature_id, feature_entries in feature_groups.items():
        feature = feature_entries[0].feature
        feature_summary = _summarize_status_entries(feature_entries)

        # Display feature file path if available
        feature_file = (
            str(feature.source_file)
            if feature.source_file
            else (
                str(feature.source_dir / "_feature.md")
                if feature.source_dir
                else f"features/{feature_id}.md"
            )
        )
        click.echo(
            f"Feature File: {feature_file} ({feature_summary.coverage_percent}%)"
        )

        # Show scenarios directly (flattened from stories)
        for entry in feature_entries:
            marker = "✓" if entry.status == "implemented" else "⚠"
            path = f"{entry.test_file}::{entry.test_function}"
            suffix = "" if entry.status == "implemented" else " (skipped)"
            click.echo(f"  {marker} {entry.scenario.scenario_id:<25} {path}{suffix}")
        click.echo("")

    click.echo(
        f"Overall: {summary.implemented}/{summary.total_scenarios} scenarios implemented ({summary.coverage_percent}%)"
    )
    if separator:
        click.echo(separator[0])


def _story_output_path(output_path: Path, feature_id: str, story_id: str) -> Path:
    return output_path / feature_id / f"test_{story_id}.py"


def _feature_output_path(output_path: Path, feature_id: str) -> Path:
    return output_path / f"test_{feature_id}.py"


def _is_single_file_feature(feature: object) -> bool:
    return getattr(feature, "source_file", None) is not None


@click.command("status")
@click.option(
    "--dir",
    "features_dir",
    default="features",
    help="Path to features directory.",
)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    show_default=True,
    help="Output format: 'table' or 'json'.",
)
@click.option("--feature", "feature_id", help="Filter by feature ID.")
@click.option("--story", "story_id", help="Filter by story ID.")
@click.option(
    "--unimplemented", is_flag=True, help="Show only unimplemented scenarios."
)
@click.option("--implemented", is_flag=True, help="Show only implemented scenarios.")
def status(
    features_dir: str,
    format_type: str,
    feature_id: str | None,
    story_id: str | None,
    unimplemented: bool,
    implemented: bool,
) -> None:
    """Show which scenarios are implemented vs. skipped."""
    from specleft.validator import load_specs_directory

    if unimplemented and implemented:
        click.secho(
            "Cannot use --implemented and --unimplemented together.", fg="red", err=True
        )
        sys.exit(1)

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

    if feature_id and not any(
        feature.feature_id == feature_id for feature in config.features
    ):
        click.secho(f"Unknown feature ID: {feature_id}", fg="red", err=True)
        sys.exit(1)

    if story_id:
        stories = [
            story
            for feature in config.features
            for story in feature.stories
            if story.story_id == story_id
        ]
        if not stories:
            click.secho(f"Unknown story ID: {story_id}", fg="red", err=True)
            sys.exit(1)

    entries = build_status_entries(
        config,
        Path("tests"),
        feature_id=feature_id,
        story_id=story_id,
    )

    if unimplemented:
        entries = [entry for entry in entries if entry.status == "skipped"]
    elif implemented:
        entries = [entry for entry in entries if entry.status == "implemented"]

    if format_type == "json":
        payload = build_status_json(entries, include_execution_time=True)
        click.echo(json.dumps(payload, indent=2))
    else:
        show_only = None
        if unimplemented:
            show_only = "unimplemented"
        elif implemented:
            show_only = "implemented"
        print_status_table(entries, show_only=show_only)
