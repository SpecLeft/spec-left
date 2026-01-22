"""Features command group."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import click

from specleft.schema import SpecsConfig
from specleft.utils.structure import warn_if_nested_structure
from specleft.utils.test_discovery import TestDiscoveryResult, discover_pytest_tests
from specleft.validator import SpecStats


def _build_features_list_json(config: SpecsConfig) -> dict[str, object]:
    from specleft.commands.formatters import build_feature_json

    features_payload: list[dict[str, object]] = []
    story_count = 0
    scenario_count = 0

    for feature in config.features:
        story_count += len(feature.stories)
        scenario_count += len(feature.all_scenarios)
        features_payload.append(build_feature_json(feature))

    return {
        "timestamp": datetime.now().isoformat(),
        "features": features_payload,
        "summary": {
            "features": len(config.features),
            "stories": story_count,
            "scenarios": scenario_count,
        },
    }


def _build_features_stats_json(
    *,
    features_dir: str,
    tests_dir: str,
    stats: SpecStats | None,
    spec_scenario_ids: set[str],
    test_discovery: TestDiscoveryResult,
) -> dict[str, object]:
    coverage_payload: dict[str, object] = {
        "scenarios_with_tests": 0,
        "scenarios_without_tests": 0,
        "coverage_percent": None,
        "uncovered_scenarios": [],
    }
    specs_payload: dict[str, object] | None
    if stats is None:
        specs_payload = None
    else:
        spec_stats = cast(Any, stats)
        specs_payload = {
            "features": spec_stats.feature_count,
            "stories": spec_stats.story_count,
            "scenarios": spec_stats.scenario_count,
            "steps": spec_stats.step_count,
            "parameterized_scenarios": spec_stats.parameterized_scenario_count,
            "tags": sorted(spec_stats.tags) if spec_stats.tags else [],
        }
        if spec_stats.scenario_count > 0:
            scenarios_with_tests = spec_scenario_ids.intersection(
                test_discovery.specleft_scenario_ids
            )
            scenarios_without_tests = (
                spec_scenario_ids - test_discovery.specleft_scenario_ids
            )
            coverage_percent = (
                len(scenarios_with_tests) / spec_stats.scenario_count * 100
            )
            coverage_payload = {
                "scenarios_with_tests": len(scenarios_with_tests),
                "scenarios_without_tests": len(scenarios_without_tests),
                "coverage_percent": round(coverage_percent, 1),
                "uncovered_scenarios": sorted(scenarios_without_tests),
            }

    return {
        "timestamp": datetime.now().isoformat(),
        "directories": {
            "features": f"{features_dir}/",
            "tests": f"{tests_dir}/",
        },
        "pytest": {
            "total_tests": test_discovery.total_tests,
            "specleft_tests": test_discovery.specleft_tests,
            "error": test_discovery.error,
        },
        "specs": specs_payload,
        "coverage": coverage_payload,
    }


@click.group()
def features() -> None:
    """Feature definition management."""
    pass


@features.command("validate")
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
@click.option(
    "--strict",
    is_flag=True,
    help="Treat warnings as errors.",
)
def features_validate(features_dir: str, format_type: str, strict: bool) -> None:
    """Validate Markdown specs in a features directory."""
    from specleft.validator import collect_spec_stats, load_specs_directory

    warnings: list[dict[str, object]] = []
    try:
        config = load_specs_directory(features_dir)
        stats = collect_spec_stats(config)

        # Gentle nudge for nested structures (table output only)
        if format_type != "json":
            warn_if_nested_structure(Path(features_dir))

        if format_type == "json":
            payload = {
                "valid": True,
                "timestamp": datetime.now().isoformat(),
                "features": stats.feature_count,
                "stories": stats.story_count,
                "scenarios": stats.scenario_count,
                "errors": [],
                "warnings": warnings,
            }
            click.echo(json.dumps(payload, indent=2))
        else:
            click.secho(f"✅ Features directory '{features_dir}/' is valid", bold=True)
            click.echo("")
            click.secho("Summary:", fg="cyan")
            click.echo(f"  Features: {stats.feature_count}")
            click.echo(f"  Stories: {stats.story_count}")
            click.echo(f"  Scenarios: {stats.scenario_count}")
            click.echo(f"  Steps: {stats.step_count}")
        if strict and warnings:
            sys.exit(2)
        sys.exit(0)
    except FileNotFoundError:
        if format_type == "json":
            payload = {
                "valid": False,
                "timestamp": datetime.now().isoformat(),
                "features": 0,
                "stories": 0,
                "scenarios": 0,
                "errors": [
                    {
                        "file": str(features_dir),
                        "message": f"Directory not found: {features_dir}",
                    }
                ],
                "warnings": warnings,
            }
            click.echo(json.dumps(payload, indent=2))
        else:
            click.secho(f"✗ Directory not found: {features_dir}", fg="red", err=True)
        sys.exit(1)
    except ValueError as e:
        if format_type == "json":
            payload = {
                "valid": False,
                "timestamp": datetime.now().isoformat(),
                "features": 0,
                "stories": 0,
                "scenarios": 0,
                "errors": [
                    {
                        "message": str(e),
                    }
                ],
                "warnings": warnings,
            }
            click.echo(json.dumps(payload, indent=2))
        else:
            click.secho(f"✗ Validation failed: {e}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        if format_type == "json":
            payload = {
                "valid": False,
                "timestamp": datetime.now().isoformat(),
                "features": 0,
                "stories": 0,
                "scenarios": 0,
                "errors": [
                    {
                        "message": f"Unexpected validation failure: {e}",
                    }
                ],
                "warnings": warnings,
            }
            click.echo(json.dumps(payload, indent=2))
        else:
            click.secho(f"✗ Unexpected validation failure: {e}", fg="red", err=True)
        sys.exit(1)


@features.command("list")
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
def features_list(features_dir: str, format_type: str) -> None:
    """List features, stories, and scenarios."""
    from specleft.validator import load_specs_directory

    try:
        config = load_specs_directory(features_dir)
    except FileNotFoundError:
        if format_type == "json":
            error_payload = {
                "status": "error",
                "message": f"Directory not found: {features_dir}",
            }
            click.echo(json.dumps(error_payload, indent=2))
        else:
            click.secho(f"✗ Directory not found: {features_dir}", fg="red", err=True)
        sys.exit(1)
    except ValueError as e:
        if format_type == "json":
            error_payload = {
                "status": "error",
                "message": f"Unable to load specs: {e}",
            }
            click.echo(json.dumps(error_payload, indent=2))
        else:
            click.secho(f"✗ Unable to load specs: {e}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        if format_type == "json":
            error_payload = {
                "status": "error",
                "message": f"Unexpected error loading specs: {e}",
            }
            click.echo(json.dumps(error_payload, indent=2))
        else:
            click.secho(f"✗ Unexpected error loading specs: {e}", fg="red", err=True)
        sys.exit(1)

    if format_type == "json":
        payload = _build_features_list_json(config)
        click.echo(json.dumps(payload, indent=2))
        return

    # Gentle nudge for nested structures
    warn_if_nested_structure(Path(features_dir))

    click.echo(f"Features ({len(config.features)}):")
    for feature in config.features:
        click.echo(f"- {feature.feature_id}: {feature.name}")
        for story in feature.stories:
            click.echo(f"  - {story.story_id}: {story.name}")
            for scenario in story.scenarios:
                click.echo(f"    - {scenario.scenario_id}: {scenario.name}")


@features.command("stats")
@click.option(
    "--dir",
    "features_dir",
    default="features",
    help="Path to features directory.",
)
@click.option(
    "--tests-dir",
    "-t",
    default="tests",
    help="Path to tests directory.",
)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    show_default=True,
    help="Output format: 'table' or 'json'.",
)
def features_stats(features_dir: str, tests_dir: str, format_type: str) -> None:
    """Show aggregate statistics for specs and test coverage."""
    from specleft.validator import collect_spec_stats, load_specs_directory

    config = None
    stats = None
    spec_scenario_ids: set[str] = set()

    try:
        config = load_specs_directory(features_dir)
        stats = collect_spec_stats(config)
        for feature in config.features:
            for story in feature.stories:
                for scenario in story.scenarios:
                    spec_scenario_ids.add(scenario.scenario_id)
    except FileNotFoundError:
        if format_type == "json":
            error_payload = {
                "status": "error",
                "message": f"Directory not found: {features_dir}",
            }
            click.echo(json.dumps(error_payload, indent=2))
        else:
            click.secho(f"✗ Directory not found: {features_dir}", fg="red", err=True)
        sys.exit(1)
    except ValueError as e:
        if "No feature specs found" in str(e):
            if format_type == "json":
                stats = None
            else:
                click.secho(f"No specs found in {features_dir}.", fg="yellow")
            stats = None
        else:
            if format_type == "json":
                error_payload = {
                    "status": "error",
                    "message": f"Unable to load specs: {e}",
                }
                click.echo(json.dumps(error_payload, indent=2))
            else:
                click.secho(f"✗ Unable to load specs: {e}", fg="red", err=True)
            sys.exit(1)
    except Exception as e:
        if format_type == "json":
            error_payload = {
                "status": "error",
                "message": f"Unexpected error loading specs: {e}",
            }
            click.echo(json.dumps(error_payload, indent=2))
        else:
            click.secho(f"✗ Unexpected error loading specs: {e}", fg="red", err=True)
        sys.exit(1)

    # Gentle nudge for nested structures (table output only)
    if format_type == "table":
        warn_if_nested_structure(Path(features_dir))

    test_discovery = discover_pytest_tests(tests_dir)

    if format_type == "json":
        payload = _build_features_stats_json(
            features_dir=features_dir,
            tests_dir=tests_dir,
            stats=stats,
            spec_scenario_ids=spec_scenario_ids,
            test_discovery=test_discovery,
        )
        click.echo(json.dumps(payload, indent=2))
        return

    click.echo("")
    click.secho("Test Coverage Stats", fg="cyan", bold=True)
    click.echo("")

    click.secho("Target Directories:", fg="cyan")
    click.echo(f"  Features Directory: {features_dir}/")
    click.secho(f"  Tests Directory: {tests_dir}/")
    click.echo("")

    click.secho("Pytest Tests:", fg="cyan")
    if test_discovery.error:
        click.secho(f"  Warning: {test_discovery.error}", fg="yellow")
    click.echo(f"  Total pytest tests discovered: {test_discovery.total_tests}")
    click.echo(f"  Tests with @specleft: {test_discovery.specleft_tests}")
    click.echo("")

    click.secho("Specifications:", fg="cyan")
    if stats:
        click.echo(f"  Features: {stats.feature_count}")
        click.echo(f"  Stories: {stats.story_count}")
        click.echo(f"  Scenarios: {stats.scenario_count}")
        click.echo(f"  Steps: {stats.step_count}")
        click.echo(f"  Parameterized scenarios: {stats.parameterized_scenario_count}")
        if stats.tags:
            click.echo(f"  Tags: {', '.join(sorted(stats.tags))}")
    else:
        click.echo("  No specs found.")
    click.echo("")

    click.secho("Coverage:", fg="cyan")
    if stats and stats.scenario_count > 0:
        scenarios_with_tests = spec_scenario_ids.intersection(
            test_discovery.specleft_scenario_ids
        )
        scenarios_without_tests = (
            spec_scenario_ids - test_discovery.specleft_scenario_ids
        )
        coverage_pct = (
            len(scenarios_with_tests) / stats.scenario_count * 100
            if stats.scenario_count > 0
            else 0
        )
        colour = (
            "green" if coverage_pct >= 80 else "yellow" if coverage_pct >= 50 else "red"
        )
        click.echo(f"  Scenarios with tests: {len(scenarios_with_tests)}")
        click.echo(f"  Scenarios without tests: {len(scenarios_without_tests)}")
        click.secho(f"  Coverage: {coverage_pct:.1f}%", fg=colour)

        if scenarios_without_tests:
            click.echo("")
            click.secho("Scenarios without tests:", fg="cyan")
            for scenario_id in sorted(scenarios_without_tests):
                click.echo(f"  - {scenario_id}")
    elif stats:
        click.echo("  No scenarios defined in specs.")
    else:
        click.echo("  Cannot calculate coverage without specs.")
