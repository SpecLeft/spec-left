"""SpecLeft CLI - Command line interface for test management."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path

import click
from jinja2 import Environment, FileSystemLoader, Template

from specleft.schema import FeatureSpec, ScenarioSpec, SpecsConfig, StorySpec
from specleft.validator import collect_spec_stats, load_specs_directory


def to_snake_case(name: str) -> str:
    """Convert a string to snake_case.

    Args:
        name: The string to convert.

    Returns:
        Snake case version of the string.
    """
    # Replace hyphens and spaces with underscores
    s = re.sub(r"[-\s]+", "_", name)
    # Insert underscore before uppercase letters and lowercase them
    s = re.sub(r"([A-Z])", r"_\1", s).lower()
    # Remove leading underscores and collapse multiple underscores
    s = re.sub(r"_+", "_", s).strip("_")
    return s


@dataclass(frozen=True)
class TestDiscoveryResult:
    """Result of pytest test discovery."""

    total_tests: int
    specleft_tests: int
    specleft_scenario_ids: frozenset[str]
    error: str | None = None


@dataclass(frozen=True)
class FileSpecleftResult:
    """Result of finding @specleft tests in a file."""

    count: int
    scenario_ids: frozenset[str]


def _discover_pytest_tests(tests_dir: str = "tests") -> TestDiscoveryResult:
    """Discover pytest tests and identify @specleft-decorated tests.

    Uses pytest --collect-only to find all tests, then parses test files
    to identify which ones have @specleft decorators.

    Args:
        tests_dir: Directory containing test files.

    Returns:
        TestDiscoveryResult with counts and scenario IDs.
    """
    tests_path = Path(tests_dir)
    if not tests_path.exists():
        return TestDiscoveryResult(
            total_tests=0,
            specleft_tests=0,
            specleft_scenario_ids=frozenset(),
            error=f"Tests directory not found: {tests_dir}",
        )

    # Use pytest --collect-only to discover tests
    try:
        result = subprocess.run(
            ["pytest", "--collect-only", "-q", tests_dir],
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout
    except FileNotFoundError:
        return TestDiscoveryResult(
            total_tests=0,
            specleft_tests=0,
            specleft_scenario_ids=frozenset(),
            error="pytest not found. Install pytest to discover tests.",
        )
    except subprocess.TimeoutExpired:
        return TestDiscoveryResult(
            total_tests=0,
            specleft_tests=0,
            specleft_scenario_ids=frozenset(),
            error="Test discovery timed out.",
        )

    # Count total tests from pytest output
    # pytest --collect-only -q output format: "X tests collected" or lines like "test_file.py::test_func"
    total_tests = 0
    for line in output.strip().split("\n"):
        line = line.strip()
        if "::" in line and not line.startswith("<"):
            total_tests += 1
        elif "test" in line.lower() and "collected" in line.lower():
            # Parse "X tests collected" or "X test collected"
            match = re.search(r"(\d+)\s+tests?\s+collected", line, re.IGNORECASE)
            if match:
                total_tests = int(match.group(1))
                break

    # Find @specleft decorated tests by parsing Python files
    specleft_tests = 0
    specleft_scenario_ids: set[str] = set()

    for py_file in tests_path.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue
        try:
            file_results = _find_specleft_tests_in_file(py_file)
            specleft_tests += file_results.count
            specleft_scenario_ids.update(file_results.scenario_ids)
        except Exception:
            # Skip files that can't be parsed
            continue

    return TestDiscoveryResult(
        total_tests=total_tests,
        specleft_tests=specleft_tests,
        specleft_scenario_ids=frozenset(specleft_scenario_ids),
    )


def _find_specleft_tests_in_file(file_path: Path) -> FileSpecleftResult:
    """Parse a Python file to find @specleft decorated test functions.

    Args:
        file_path: Path to the Python file.

    Returns:
        FileSpecleftResult with count and scenario_ids.
    """
    content = file_path.read_text()
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return FileSpecleftResult(count=0, scenario_ids=frozenset())

    count = 0
    scenario_ids: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                scenario_id = _extract_specleft_scenario_id(decorator)
                if scenario_id is not None:
                    count += 1
                    scenario_ids.add(scenario_id)

    return FileSpecleftResult(count=count, scenario_ids=frozenset(scenario_ids))


def _extract_specleft_scenario_id(decorator: ast.expr) -> str | None:
    """Extract scenario_id from a @specleft(...) decorator.

    Args:
        decorator: AST node for the decorator.

    Returns:
        The scenario_id if this is a @specleft decorator, None otherwise.
    """
    # Handle @specleft(feature_id="...", scenario_id="...")
    if isinstance(decorator, ast.Call):
        func = decorator.func
        # Check if it's specleft(...) or module.specleft(...)
        if (
            isinstance(func, ast.Name)
            and func.id == "specleft"
            or isinstance(func, ast.Attribute)
            and func.attr == "specleft"
        ):
            return _get_scenario_id_from_call(decorator)
    return None


def _get_scenario_id_from_call(call: ast.Call) -> str | None:
    """Extract scenario_id from a function call's arguments."""
    # Check keyword arguments
    for keyword in call.keywords:
        if keyword.arg == "scenario_id" and isinstance(keyword.value, ast.Constant):
            return str(keyword.value.value)
    # Check positional arguments (scenario_id is second positional arg)
    if len(call.args) >= 2 and isinstance(call.args[1], ast.Constant):
        return str(call.args[1].value)
    return None


@dataclass(frozen=True)
class ScenarioPlan:
    """Metadata for a planned scenario output."""

    feature_id: str
    feature_name: str
    story_id: str
    story_name: str
    scenario: ScenarioSpec


@dataclass(frozen=True)
class SkeletonPlan:
    """Plan for generating a skeleton test file."""

    feature: FeatureSpec | None
    story: StorySpec | None
    scenarios: list[ScenarioPlan]
    output_path: Path
    content: str
    preview_content: str


@dataclass(frozen=True)
class SkeletonSummary:
    """Summary of skeleton generation steps."""

    feature_count: int
    story_count: int
    scenario_count: int
    output_paths: list[Path]


@dataclass(frozen=True)
class SkeletonPlanResult:
    """Result of skeleton planning."""

    plans: list[SkeletonPlan]
    skipped_paths: list[Path]


def _load_skeleton_template() -> Template:
    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["snake_case"] = to_snake_case
    env.filters["repr"] = repr
    return env.get_template("skeleton_test.py.jinja2")


def _story_output_path(output_path: Path, feature_id: str, story_id: str) -> Path:
    return output_path / feature_id / f"test_{story_id}.py"


def _feature_with_story(feature: FeatureSpec, story: StorySpec) -> FeatureSpec:
    return feature.model_copy(update={"stories": [story]})


def _plan_skeleton_generation(
    config: SpecsConfig,
    output_path: Path,
    template: Template,
    single_file: bool,
) -> SkeletonPlanResult:
    plans: list[SkeletonPlan] = []
    skipped_paths: list[Path] = []
    if single_file:
        target_path = output_path / "test_generated.py"
        if target_path.exists():
            skipped_paths.append(target_path)
            return SkeletonPlanResult(plans=plans, skipped_paths=skipped_paths)
        content = template.render(features=config.features)
        scenario_plans = [
            ScenarioPlan(
                feature_id=feature.feature_id,
                feature_name=feature.name,
                story_id=story.story_id,
                story_name=story.name,
                scenario=scenario,
            )
            for feature in config.features
            for story in feature.stories
            for scenario in story.scenarios
        ]
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
            )
        )
        return SkeletonPlanResult(plans=plans, skipped_paths=skipped_paths)

    for feature in config.features:
        for story in feature.stories:
            target_path = _story_output_path(
                output_path, feature.feature_id, story.story_id
            )
            if target_path.exists():
                skipped_paths.append(target_path)
                continue
            content = template.render(features=[_feature_with_story(feature, story)])
            scenario_plans = [
                ScenarioPlan(
                    feature_id=feature.feature_id,
                    feature_name=feature.name,
                    story_id=story.story_id,
                    story_name=story.name,
                    scenario=scenario,
                )
                for scenario in story.scenarios
            ]
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
                )
            )

    return SkeletonPlanResult(plans=plans, skipped_paths=skipped_paths)


def _summarize_skeleton_plans(
    plans: list[SkeletonPlan],
) -> SkeletonSummary:
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


@click.group()
@click.version_option(version="0.2.0", prog_name="specleft")
def cli() -> None:
    """SpecLeft - Code-driven test case management for Python."""
    pass


# TEST commands group
@cli.group()
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
def skeleton(
    features_dir: str, output_dir: str, single_file: bool, skip_preview: bool
) -> None:
    """Generate skeleton test files from Markdown feature specs.

    Reads the features directory specification and generates pytest test files
    with @specleft decorators and step context managers.
    """
    # Load and validate specs directory
    try:
        config = load_specs_directory(features_dir)
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

    template = _load_skeleton_template()
    output_path = Path(output_dir)
    plan_result = _plan_skeleton_generation(
        config=config,
        output_path=output_path,
        template=template,
        single_file=single_file,
    )

    if plan_result.skipped_paths:
        for skipped_path in plan_result.skipped_paths:
            click.secho(f"Skipped existing file: {skipped_path}", fg="yellow")

    if not plan_result.plans:
        click.secho("No new skeleton tests to generate.", fg="magenta")
        return

    summary = _summarize_skeleton_plans(plan_result.plans)

    click.secho("\nSkeleton Generation Plan", fg="magenta", bold=True)
    click.echo(f"  Features: {summary.feature_count}")
    click.echo(f"  Stories: {summary.story_count}")
    click.echo(f"  Scenarios: {summary.scenario_count}")
    click.echo(f"  Files to create: {len(summary.output_paths)}")
    click.echo("")
    click.secho("Planned test files:", fg="cyan")
    for output_path in summary.output_paths:
        click.echo(f"    - {output_path}")

    for i, plan in enumerate(plan_result.plans):
        if not skip_preview:
            _render_skeleton_preview(plan)
            if not click.confirm(
                f"{i+1}/{len(plan_result.plans)} Create this test file ({plan.output_path})?",
                default=False,
            ):
                click.secho("Skipped test creation.", fg="yellow")
                continue

        plan.output_path.parent.mkdir(parents=True, exist_ok=True)
        plan.output_path.write_text(plan.content)
        click.echo("")
        click.echo(f"✅ Created: {plan.output_path}")

    click.secho("\nNext steps:", fg="cyan", bold=True)
    click.echo(f"  1. Implement test logic in {output_dir}/")
    click.echo(f"  2. Run tests: pytest {output_dir if output_dir else ''}/")
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
def report(results_file: str | None, output: str, open_browser: bool) -> None:
    """Generate HTML report from test results.

    Reads the test results JSON and generates a static HTML report
    with summary dashboard, feature breakdown, and step details.
    """
    results_dir = Path(".specleft/results")

    # Find results file
    if results_file:
        results_path = Path(results_file)
        if not results_path.exists():
            click.secho(
                f"Error: Results file not found: {results_file}", fg="red", err=True
            )
            sys.exit(1)
    else:
        # Find latest results file
        if not results_dir.exists():
            click.secho(
                "No results found. Run tests first with pytest.", fg="yellow", err=True
            )
            sys.exit(1)

        json_files = sorted(results_dir.glob("results_*.json"))
        if not json_files:
            click.secho("No results files found.", fg="yellow", err=True)
            sys.exit(1)

        results_path = json_files[-1]
        click.echo(f"Using latest results: {results_path}")

    # Load results
    try:
        with results_path.open() as f:
            results = json.load(f)
    except json.JSONDecodeError as e:
        click.secho(f"Invalid JSON in results file: {e}", fg="red", err=True)
        sys.exit(1)

    # Setup Jinja2 environment
    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=True,
    )

    template = env.get_template("report.html.jinja2")

    # Generate report
    html_content = template.render(results=results)

    # Write report
    output_path = Path(output)
    output_path.write_text(html_content)
    click.secho(f"Report generated: {output_path.absolute()}", fg="green")

    # Open in browser if requested
    if open_browser:
        webbrowser.open(f"file://{output_path.absolute()}")


# FEATURES commands group
@cli.group()
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
def features_validate(features_dir: str) -> None:
    """Validate Markdown specs in a features directory.

    Checks that the specs directory is valid according to the SpecLeft schema.
    Returns exit code 0 if valid, 1 if invalid.
    """
    try:
        config = load_specs_directory(features_dir)
        stats = collect_spec_stats(config)
        click.secho(f"✅ Features directory '{features_dir}/' is valid", bold=True)
        click.echo("")
        click.secho("Summary:", fg="cyan")
        click.echo(f"  Features: {stats.feature_count}")
        click.echo(f"  Stories: {stats.story_count}")
        click.echo(f"  Scenarios: {stats.scenario_count}")
        click.echo(f"  Steps: {stats.step_count}")
        sys.exit(0)
    except FileNotFoundError:
        click.secho(f"✗ Directory not found: {features_dir}", fg="red", err=True)
        sys.exit(1)
    except ValueError as e:
        click.secho(f"✗ Validation failed: {e}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"✗ Unexpected validation failure: {e}", fg="red", err=True)
        sys.exit(1)


@features.command("list")
@click.option(
    "--dir",
    "features_dir",
    default="features",
    help="Path to features directory.",
)
def features_list(features_dir: str) -> None:
    """List features, stories, and scenarios."""
    try:
        config = load_specs_directory(features_dir)
    except FileNotFoundError:
        click.secho(f"✗ Directory not found: {features_dir}", fg="red", err=True)
        sys.exit(1)
    except ValueError as e:
        click.secho(f"✗ Unable to load specs: {e}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"✗ Unexpected error loading specs: {e}", fg="red", err=True)
        sys.exit(1)

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
def features_stats(features_dir: str, tests_dir: str) -> None:
    """Show aggregate statistics for specs and test coverage."""
    # Load specs (optional - stats can work without specs)
    config = None
    stats = None
    spec_scenario_ids: set[str] = set()

    try:
        config = load_specs_directory(features_dir)
        stats = collect_spec_stats(config)
        # Collect all scenario IDs from specs
        for feature in config.features:
            for story in feature.stories:
                for scenario in story.scenarios:
                    spec_scenario_ids.add(scenario.scenario_id)
    except FileNotFoundError:
        click.secho(f"✗ Directory not found: {features_dir}", fg="red", err=True)
        sys.exit(1)
    except ValueError as e:
        if "No feature specs found" in str(e):
            click.secho(f"No specs found in {features_dir}.", fg="yellow")
            stats = None
        else:
            click.secho(f"✗ Unable to load specs: {e}", fg="red", err=True)
            sys.exit(1)
    except Exception as e:
        click.secho(f"✗ Unexpected error loading specs: {e}", fg="red", err=True)
        sys.exit(1)

    # Discover pytest tests
    test_discovery = _discover_pytest_tests(tests_dir)

    # Output stats
    click.echo("")
    click.secho("Test Coverage Stats", fg="cyan", bold=True)
    click.echo("")

    # Directories section
    click.secho("Target Directories:", fg="cyan")
    click.echo(f"  Features Directory: {features_dir}/")
    click.secho(f"  Tests Directory: {tests_dir}/")
    click.echo("")

    # Pytest tests section
    click.secho("Pytest Tests:", fg="cyan")
    if test_discovery.error:
        click.secho(f"  Warning: {test_discovery.error}", fg="yellow")
    click.echo(f"  Total pytest tests discovered: {test_discovery.total_tests}")
    click.echo(f"  Tests with @specleft: {test_discovery.specleft_tests}")
    click.echo("")

    # Specs section
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

    # Coverage section
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


if __name__ == "__main__":
    cli()
