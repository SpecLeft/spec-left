"""Test command group."""

from __future__ import annotations

import json
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

import click
from jinja2 import Environment, FileSystemLoader, Template

from specleft.commands.formatters import get_priority_value
from specleft.commands.types import (
    ScenarioPlan,
    SkeletonPlan,
    SkeletonPlanResult,
    SkeletonScenarioEntry,
    SkeletonSkipPlan,
    SkeletonSummary,
)
from specleft.schema import FeatureSpec, SpecsConfig, StorySpec
from specleft.utils.structure import detect_features_layout, warn_if_nested_structure
from specleft.utils.text import to_snake_case
from specleft.validator import load_specs_directory
from jinja2 import select_autoescape


def _load_skeleton_template() -> Template:
    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=select_autoescape(enabled_extensions=("html", "xml")),
    )
    env.filters["snake_case"] = to_snake_case
    env.filters["repr"] = repr
    return env.get_template("skeleton_test.py.jinja2")


def _story_output_path(output_path: Path, feature_id: str, story_id: str) -> Path:
    return output_path / feature_id / f"test_{story_id}.py"


def _feature_output_path(output_path: Path, feature_id: str) -> Path:
    """Output path for single-file features: tests/test_<feature_id>.py"""
    return output_path / f"test_{feature_id}.py"


def _feature_with_story(feature: FeatureSpec, story: StorySpec) -> FeatureSpec:
    return feature.model_copy(update={"stories": [story]})


def _plan_skeleton_generation(
    config: SpecsConfig,
    output_path: Path,
    template: Template,
    single_file: bool,
    force: bool,
    *,
    features_dir: Path | None = None,
) -> SkeletonPlanResult:
    """Plan skeleton test generation.

    Auto-detects layout if features_dir is provided:
    - single-file layout: generates tests/test_<feature>.py per feature
    - nested layout: generates tests/<feature>/test_<story>.py per story
    """
    plans: list[SkeletonPlan] = []
    skipped_plans: list[SkeletonSkipPlan] = []

    # Handle explicit --single-file flag
    if single_file:
        target_path = output_path / "test_generated.py"
        if target_path.exists() and not force:
            skipped_plans.append(
                SkeletonSkipPlan(
                    scenarios=_build_scenario_plans(config.features),
                    output_path=target_path,
                    reason="File already exists",
                )
            )
            return SkeletonPlanResult(plans=plans, skipped_plans=skipped_plans)
        content = template.render(features=config.features)
        scenario_plans = _build_scenario_plans(config.features)
        preview_content = _render_skeleton_preview_content(
            template=template, scenarios=scenario_plans
        )
        plans.append(
            SkeletonPlan(
                feature=None,
                story=None,
                scenarios=scenario_plans,
                output_path=target_path,
                content=content,
                preview_content=preview_content,
                overwrites=target_path.exists(),
            )
        )
        return SkeletonPlanResult(plans=plans, skipped_plans=skipped_plans)

    # Auto-detect layout if features_dir provided
    use_per_feature = False
    if features_dir is not None:
        layout = detect_features_layout(features_dir)
        use_per_feature = layout in ("single-file", "mixed", "empty")

    if use_per_feature:
        # Single-file layout: one test file per feature
        return _plan_per_feature_skeleton(
            config=config,
            output_path=output_path,
            template=template,
            force=force,
        )

    # Nested layout: one test file per story (existing behavior)
    for feature in config.features:
        for story in feature.stories:
            target_path = _story_output_path(
                output_path, feature.feature_id, story.story_id
            )
            scenario_plans = _build_story_scenario_plans(feature, story)
            if target_path.exists() and not force:
                skipped_plans.append(
                    SkeletonSkipPlan(
                        scenarios=scenario_plans,
                        output_path=target_path,
                        reason="File already exists",
                    )
                )
                continue
            content = template.render(features=[_feature_with_story(feature, story)])
            preview_content = _render_skeleton_preview_content(
                template=template, scenarios=scenario_plans
            )
            plans.append(
                SkeletonPlan(
                    feature=feature,
                    story=story,
                    scenarios=scenario_plans,
                    output_path=target_path,
                    content=content,
                    preview_content=preview_content,
                    overwrites=target_path.exists(),
                )
            )

    return SkeletonPlanResult(plans=plans, skipped_plans=skipped_plans)


def _plan_per_feature_skeleton(
    config: SpecsConfig,
    output_path: Path,
    template: Template,
    force: bool,
) -> SkeletonPlanResult:
    """Plan skeleton generation with one test file per feature."""
    plans: list[SkeletonPlan] = []
    skipped_plans: list[SkeletonSkipPlan] = []

    for feature in config.features:
        target_path = _feature_output_path(output_path, feature.feature_id)
        scenario_plans = _build_scenario_plans([feature])

        if target_path.exists() and not force:
            skipped_plans.append(
                SkeletonSkipPlan(
                    scenarios=scenario_plans,
                    output_path=target_path,
                    reason="File already exists",
                )
            )
            continue

        content = template.render(features=[feature])
        preview_content = _render_skeleton_preview_content(
            template=template, scenarios=scenario_plans
        )
        plans.append(
            SkeletonPlan(
                feature=feature,
                story=None,
                scenarios=scenario_plans,
                output_path=target_path,
                content=content,
                preview_content=preview_content,
                overwrites=target_path.exists(),
            )
        )

    return SkeletonPlanResult(plans=plans, skipped_plans=skipped_plans)


def _build_scenario_plans(features: list[FeatureSpec]) -> list[ScenarioPlan]:
    return [
        ScenarioPlan(
            feature_id=feature.feature_id,
            feature_name=feature.name,
            story_id=story.story_id,
            story_name=story.name,
            scenario=scenario,
        )
        for feature in features
        for story in feature.stories
        for scenario in story.scenarios
    ]


def _build_story_scenario_plans(
    feature: FeatureSpec, story: StorySpec
) -> list[ScenarioPlan]:
    return [
        ScenarioPlan(
            feature_id=feature.feature_id,
            feature_name=feature.name,
            story_id=story.story_id,
            story_name=story.name,
            scenario=scenario,
        )
        for scenario in story.scenarios
    ]


def _summarize_skeleton_plans(plans: list[SkeletonPlan]) -> SkeletonSummary:
    feature_ids = {scenario.feature_id for plan in plans for scenario in plan.scenarios}
    story_keys = {
        (scenario.feature_id, scenario.story_id)
        for plan in plans
        for scenario in plan.scenarios
    }
    scenario_count = sum(len(plan.scenarios) for plan in plans)
    return SkeletonSummary(
        feature_count=len(feature_ids),
        story_count=len(story_keys),
        scenario_count=scenario_count,
        output_paths=[plan.output_path for plan in plans],
    )


def _render_skeleton_preview_content(
    template: Template, scenarios: list[ScenarioPlan]
) -> str:
    if not scenarios:
        return ""

    scenario_plan = scenarios[0]
    feature = FeatureSpec(
        feature_id=scenario_plan.feature_id, name=scenario_plan.feature_name
    )
    story = StorySpec(
        story_id=scenario_plan.story_id,
        name=scenario_plan.story_name,
        scenarios=[scenario_plan.scenario],
    )
    feature.stories.append(story)
    return template.render(features=[feature])


def _render_skeleton_preview(plan: SkeletonPlan) -> None:
    click.echo("\n" + "-" * 72)
    click.echo(f"File: {plan.output_path}")
    if plan.feature is not None:
        click.echo(f"Feature: {plan.feature.feature_id}")
    else:
        feature_ids = sorted({scenario.feature_id for scenario in plan.scenarios})
        if feature_ids:
            click.echo("Features: " + ", ".join(feature_ids))

    if plan.story is not None:
        click.echo(f"Story: {plan.story.story_id}")
    else:
        story_ids = sorted({scenario.story_id for scenario in plan.scenarios})
        if story_ids:
            click.echo("Stories: " + ", ".join(story_ids))

    click.echo(f"Scenarios: {len(plan.scenarios)}")
    if plan.scenarios:
        click.echo(
            "Scenario IDs: "
            + ", ".join(scenario.scenario.scenario_id for scenario in plan.scenarios)
        )
        click.echo(f"Steps (first scenario): {len(plan.scenarios[0].scenario.steps)}")
    click.echo("Status: SKIPPED (not implemented)")
    click.echo("Preview:\n")
    click.echo(plan.preview_content.rstrip())
    click.echo("\n" + "-" * 72)


def _flatten_skeleton_entries(
    plan_result: SkeletonPlanResult,
) -> list[SkeletonScenarioEntry]:
    entries: list[SkeletonScenarioEntry] = []
    for plan in plan_result.plans:
        for scenario in plan.scenarios:
            entries.append(
                SkeletonScenarioEntry(
                    scenario=scenario,
                    output_path=plan.output_path,
                    overwrites=plan.overwrites,
                )
            )
    for skipped_plan in plan_result.skipped_plans:
        for scenario in skipped_plan.scenarios:
            entries.append(
                SkeletonScenarioEntry(
                    scenario=scenario,
                    output_path=skipped_plan.output_path,
                    overwrites=False,
                    skip_reason=skipped_plan.reason,
                )
            )
    return entries


def _build_skeleton_json(
    *,
    would_create: list[SkeletonScenarioEntry],
    would_skip: list[SkeletonScenarioEntry],
    dry_run: bool,
    template: Template,
) -> dict[str, object]:
    def _entry_payload(entry: SkeletonScenarioEntry) -> dict[str, object]:
        preview_lines = _render_skeleton_preview_content(
            template=template,
            scenarios=[entry.scenario],
        ).splitlines()
        preview = "\n".join(preview_lines[:6])
        scenario = entry.scenario.scenario
        return {
            "feature_id": entry.scenario.feature_id,
            "story_id": entry.scenario.story_id,
            "scenario_id": scenario.scenario_id,
            "test_file": str(entry.output_path),
            "test_function": scenario.test_function_name,
            "steps": len(scenario.steps),
            "priority": get_priority_value(scenario),
            "preview": preview,
            "overwrites": entry.overwrites,
        }

    return {
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "would_create": [_entry_payload(entry) for entry in would_create],
        "would_skip": [
            {
                "scenario_id": entry.scenario.scenario.scenario_id,
                "test_file": str(entry.output_path),
                "reason": entry.skip_reason,
            }
            for entry in would_skip
        ],
        "summary": {
            "would_create": len({entry.output_path for entry in would_create}),
            "would_skip": len({entry.output_path for entry in would_skip}),
        },
    }


def _print_skeleton_plan_table(
    *,
    would_create: list[SkeletonScenarioEntry],
    would_skip: list[SkeletonScenarioEntry],
    dry_run: bool,
) -> None:
    title = "Skeleton Generation Plan"
    click.echo(title)
    click.echo("━" * 58)
    if dry_run:
        click.echo("Dry run: no files will be created.")
        click.echo("")

    create_label = "Would" if dry_run else "Will"
    skip_label = "Would" if dry_run else "Will"

    if would_create:
        click.echo(f"{create_label} create tests:")
        for entry in would_create:
            scenario = entry.scenario.scenario
            click.echo(f"  ✓ {entry.output_path}::{scenario.test_function_name}")
            click.echo(
                f"    Feature: {entry.scenario.feature_id} | Story: {entry.scenario.story_id} | Scenario: {scenario.scenario_id}"
            )
            click.echo(
                f"    Steps: {len(scenario.steps)} | Priority: {get_priority_value(scenario)}"
            )
            click.echo("")
    else:
        click.echo(f"{create_label} create tests: none")
        click.echo("")

    if would_skip:
        click.echo(f"{skip_label} skip:")
        for entry in would_skip:
            scenario = entry.scenario.scenario
            click.echo(
                f"  ⚠ {entry.output_path}::{scenario.test_function_name} ({entry.skip_reason})"
            )
    else:
        click.echo(f"{skip_label} skip: none")

    create_paths = {entry.output_path for entry in would_create}
    skip_paths = {entry.output_path for entry in would_skip}
    click.echo("")
    click.echo("Summary:")
    click.echo(f"  {len(create_paths)} test files {create_label.lower()} be created")
    click.echo(f"  {len(skip_paths)} files {skip_label.lower()} be skipped")
    if dry_run:
        click.echo("\nRun without --dry-run to create files.")
    click.echo("━" * 58)


@click.group()
def test() -> None:
    """Test lifecycle commands."""
    pass


@test.command("skeleton")
@click.option(
    "--features-dir",
    "-f",
    default="features",
    help="Path to features directory.",
)
@click.option(
    "--output-dir",
    "-o",
    default="tests",
    help="Output directory for generated test files.",
)
@click.option(
    "--single-file",
    is_flag=True,
    help="Generate all tests in a single file (test_generated.py).",
)
@click.option(
    "--skip-preview",
    is_flag=True,
    help="Skip the preview of the generated skeleton tests before creating files.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be created without writing files.",
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
    "--force",
    is_flag=True,
    help="Overwrite existing test files.",
)
def skeleton(
    features_dir: str,
    output_dir: str,
    single_file: bool,
    skip_preview: bool,
    dry_run: bool,
    format_type: str,
    force: bool,
) -> None:
    """Generate skeleton test files from Markdown feature specs."""
    if format_type == "json" and not dry_run and not force:
        click.secho(
            "JSON output requires --dry-run or --force to avoid prompts.",
            fg="red",
            err=True,
        )
        sys.exit(1)

    try:
        config = load_specs_directory(features_dir, warn_on_duplicate_scenarios=True)
    except FileNotFoundError:
        click.secho(f"Error: {features_dir} not found", fg="red", err=True)
        click.echo("Create a features directory with Markdown specs to continue.")
        sys.exit(1)
    except ValueError as e:
        if "No feature specs found" in str(e):
            click.secho(f"No specs found in {features_dir}.", fg="yellow")
            return
        click.secho(f"Error loading specs from {features_dir}: {e}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(
            f"Unexpected error loading specs from {features_dir}: {e}",
            fg="red",
            err=True,
        )
        sys.exit(1)

    # Gentle nudge for nested structures (table output only)
    if format_type == "table":
        warn_if_nested_structure(Path(features_dir))

    template = _load_skeleton_template()
    output_path = Path(output_dir)
    plan_result = _plan_skeleton_generation(
        config=config,
        output_path=output_path,
        template=template,
        single_file=single_file,
        force=force,
        features_dir=Path(features_dir),
    )

    flattened = _flatten_skeleton_entries(plan_result)
    would_create = [entry for entry in flattened if entry.skip_reason is None]
    would_skip = [entry for entry in flattened if entry.skip_reason is not None]

    if format_type == "json":
        payload = _build_skeleton_json(
            would_create=would_create,
            would_skip=would_skip,
            dry_run=dry_run,
            template=template,
        )
        click.echo(json.dumps(payload, indent=2))
    else:
        _print_skeleton_plan_table(
            would_create=would_create,
            would_skip=would_skip,
            dry_run=dry_run,
        )
        if not skip_preview:
            for plan in plan_result.plans:
                _render_skeleton_preview(plan)

    if dry_run:
        return

    if not plan_result.plans:
        click.secho("No new skeleton tests to generate.", fg="magenta")
        return

    if not force and not click.confirm("Confirm creation?", default=False):
        click.echo("Cancelled")
        sys.exit(2)

    for plan in plan_result.plans:
        plan.output_path.parent.mkdir(parents=True, exist_ok=True)
        plan.output_path.write_text(plan.content)

    if format_type == "table":
        click.secho(f"\n✓ Created {len(plan_result.plans)} test files", fg="green")
        for plan in plan_result.plans:
            click.echo(f"{plan.output_path}")
        click.secho("\nNext steps:", fg="cyan", bold=True)
        click.echo(f"  1. Implement test logic in {output_dir.removesuffix('/')}/")
        click.echo(f"  2. Run tests: pytest {output_dir.removesuffix('/')}/")
        click.echo("  3. View report: specleft test report")


@test.command("report")
@click.option(
    "--results-file",
    "-r",
    help="Specific results JSON file. If not provided, uses latest.",
)
@click.option(
    "--output",
    "-o",
    default="report.html",
    help="Output HTML file path.",
)
@click.option(
    "--open-browser",
    is_flag=True,
    help="Open the report in the default web browser.",
)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    show_default=True,
    help="Output format: 'table' or 'json'.",
)
def report(
    results_file: str | None, output: str, open_browser: bool, format_type: str
) -> None:
    """Generate HTML report from test results."""
    results_dir = Path(".specleft/results")

    if results_file:
        results_path = Path(results_file)
        if not results_path.exists():
            if format_type == "json":
                payload = {
                    "status": "error",
                    "message": f"Results file not found: {results_file}",
                }
                click.echo(json.dumps(payload, indent=2))
            else:
                click.secho(
                    f"Error: Results file not found: {results_file}", fg="red", err=True
                )
            sys.exit(1)
    else:
        if not results_dir.exists():
            if format_type == "json":
                payload = {
                    "status": "error",
                    "message": "No results found. Run tests first with pytest.",
                }
                click.echo(json.dumps(payload, indent=2))
            else:
                click.secho(
                    "No results found. Run tests first with pytest.",
                    fg="yellow",
                    err=True,
                )
            sys.exit(1)

        json_files = sorted(results_dir.glob("results_*.json"))
        if not json_files:
            if format_type == "json":
                payload = {
                    "status": "error",
                    "message": "No results files found.",
                }
                click.echo(json.dumps(payload, indent=2))
            else:
                click.secho("No results files found.", fg="yellow", err=True)
            sys.exit(1)

        results_path = json_files[-1]
        if format_type == "table":
            click.echo(f"Using latest results: {results_path}")

    try:
        with results_path.open() as f:
            results = json.load(f)
    except json.JSONDecodeError as e:
        if format_type == "json":
            payload = {
                "status": "error",
                "message": f"Invalid JSON in results file: {e}",
            }
            click.echo(json.dumps(payload, indent=2))
        else:
            click.secho(f"Invalid JSON in results file: {e}", fg="red", err=True)
        sys.exit(1)

    if format_type == "json":
        payload = {
            "status": "ok",
            "results_file": str(results_path),
            "summary": results.get("summary"),
            "features": results.get("features"),
        }
        click.echo(json.dumps(payload, indent=2))
        return

    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=True,
    )

    template = env.get_template("report.html.jinja2")
    html_content = template.render(results=results)

    output_path = Path(output)
    output_path.write_text(html_content)
    click.secho(f"Report generated: {output_path.absolute()}", fg="green")

    if open_browser:
        webbrowser.open(f"file://{output_path.absolute()}")
