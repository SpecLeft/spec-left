"""SpecLeft CLI - Command line interface for test management."""

from __future__ import annotations

import json
import re
import sys
import webbrowser
from pathlib import Path

import click
from jinja2 import Environment, FileSystemLoader

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
def skeleton(features_dir: str, output_dir: str, single_file: bool) -> None:
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
        click.secho(f"Error loading specs from {features_dir}: {e}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(
            f"Unexpected error loading specs from {features_dir}: {e}",
            fg="red",
            err=True,
        )
        sys.exit(1)

    # Setup Jinja2 environment
    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Add custom filters
    env.filters["snake_case"] = to_snake_case
    env.filters["repr"] = repr

    template = env.get_template("skeleton_test.py.jinja2")

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if single_file:
        # Generate all tests in one file
        content = template.render(features=config.features)
        output_file = output_path / "test_generated.py"
        output_file.write_text(content)
        click.secho(f"Generated: {output_file}", fg="green")
    else:
        # Generate one file per feature
        for feature in config.features:
            content = template.render(features=[feature])
            filename = f"test_{feature.feature_id.lower().replace('-', '_')}.py"
            output_file = output_path / filename
            output_file.write_text(content)
            click.secho(f"Generated: {output_file}", fg="green")

    # Summary
    total_scenarios = sum(
        len(story.scenarios) for feature in config.features for story in feature.stories
    )
    click.echo(
        f"\nGenerated {len(config.features)} feature(s) "
        f"with {total_scenarios} scenario(s)"
    )
    click.echo("\nNext steps:")
    click.echo(f"  1. Implement test logic in {output_dir}/")
    click.echo("  2. Run tests: pytest")
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
        click.secho(f"✓ Features directory '{features_dir}/' is valid", fg="green")
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
def features_stats(features_dir: str) -> None:
    """Show aggregate statistics for specs."""
    try:
        config = load_specs_directory(features_dir)
        stats = collect_spec_stats(config)
    except FileNotFoundError:
        click.secho(f"✗ Directory not found: {features_dir}", fg="red", err=True)
        sys.exit(1)
    except ValueError as e:
        click.secho(f"✗ Unable to load specs: {e}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"✗ Unexpected error loading specs: {e}", fg="red", err=True)
        sys.exit(1)

    click.echo("Spec stats:")
    click.echo(f"  Features: {stats.feature_count}")
    click.echo(f"  Stories: {stats.story_count}")
    click.echo(f"  Scenarios: {stats.scenario_count}")
    click.echo(f"  Steps: {stats.step_count}")
    click.echo(f"  Parameterized scenarios: {stats.parameterized_scenario_count}")
    if stats.tags:
        click.echo(f"  Tags: {', '.join(sorted(stats.tags))}")


if __name__ == "__main__":
    cli()
