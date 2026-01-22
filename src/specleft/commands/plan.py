"""Planning command for SpecLeft."""

from __future__ import annotations

import json
import textwrap
from datetime import datetime
from pathlib import Path

import click
from slugify import slugify

SUGGESTED_PRD_LOCATIONS = (Path("prd.md"), Path("docs/prd.md"))


def _read_prd(prd_path: Path) -> tuple[str | None, list[str]]:
    warnings: list[str] = []
    if not prd_path.exists():
        warnings.append(f"PRD not found at {prd_path}")
        return None, warnings

    try:
        return prd_path.read_text(), warnings
    except OSError as exc:
        warnings.append(f"Unable to read PRD at {prd_path}: {exc}")
        return None, warnings


def _extract_feature_titles(prd_content: str) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    lines = [line.rstrip() for line in prd_content.splitlines()]
    h1_titles = [line[2:].strip() for line in lines if line.startswith("# ")]
    h2_titles = [line[3:].strip() for line in lines if line.startswith("## ")]

    if h2_titles:
        return [title for title in h2_titles if title], warnings

    if len(h1_titles) == 1 and h1_titles[0]:
        warnings.append("No secondary headings found; using top-level title.")
        return [h1_titles[0]], warnings

    warnings.append("No usable headings found; creating features/prd.md.")
    return [], warnings


def _feature_template(title: str) -> str:
    return (
        textwrap.dedent(
            f"""
            # Feature: {title}

            ## Scenarios

            ### Scenario: Example
            priority: medium

            - Given a precondition
            - When an action occurs
            - Then the expected result
            """
        ).strip()
        + "\n"
    )


def _feature_path(features_dir: Path, title: str) -> Path:
    slug = "prd" if title == "PRD" else slugify(title)
    return features_dir / f"{slug}.md"


def _feature_paths(features_dir: Path, titles: list[str]) -> list[Path]:
    return [_feature_path(features_dir, title) for title in titles]


def _needs_skip(path: Path) -> bool:
    return path.exists()


def _apply_plan(
    titles: list[str],
    *,
    features_dir: Path,
    dry_run: bool,
) -> tuple[list[Path], list[Path]]:
    created: list[Path] = []
    skipped: list[Path] = []
    for title in titles:
        path = _feature_path(features_dir, title)
        if _needs_skip(path):
            skipped.append(path)
            continue
        if dry_run:
            created.append(path)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_feature_template(title))
        created.append(path)
    return created, skipped


def _build_plan_payload(
    *,
    prd_path: Path,
    dry_run: bool,
    feature_count: int,
    created: list[Path],
    skipped: list[Path],
    warnings: list[str],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "timestamp": datetime.now().isoformat(),
        "status": "warning" if warnings else "ok",
        "prd_path": str(prd_path),
        "dry_run": dry_run,
        "feature_count": feature_count,
        "warnings": warnings,
        "suggested_locations": [str(path) for path in SUGGESTED_PRD_LOCATIONS],
        "skipped": [str(path) for path in skipped],
    }
    if dry_run:
        payload["would_create"] = [str(path) for path in created]
    else:
        payload["created"] = [str(path) for path in created]
    return payload


def _print_warning(message: str) -> None:
    click.secho(f"Warning: {message}", fg="yellow")


def _print_plan_summary(*, feature_count: int, dry_run: bool) -> None:
    click.echo("Planning feature specs...")
    if dry_run:
        click.echo("Dry run: no files will be created.")
    click.echo(f"Features planned: {feature_count}")


def _print_plan_results(
    *,
    created: list[Path],
    skipped: list[Path],
    dry_run: bool,
) -> None:
    if dry_run:
        click.echo("Would create:")
    else:
        click.echo("Created:")
    for path in created:
        click.echo(f"  - {path}")

    if skipped:
        click.echo("Skipped existing:")
        for path in skipped:
            click.echo(f"  - {path}")


@click.command(
    "plan",
    epilog=(
        "Feature files may include optional metadata (confidence, assumptions, tags, "
        "owner, etc). See docs/feature-template.md for details."
    ),
)
@click.option(
    "--from",
    "prd_path",
    default="prd.md",
    help="Path to the PRD file.",
)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    show_default=True,
    help="Output format: 'table' or 'json'.",
)
@click.option("--dry-run", is_flag=True, help="Preview without writing files.")
def plan(prd_path: str, format_type: str, dry_run: bool) -> None:
    """Generate feature specs from a PRD."""
    prd_file = Path(prd_path)
    prd_content, warnings = _read_prd(prd_file)
    if prd_content is None:
        if format_type == "json":
            payload = _build_plan_payload(
                prd_path=prd_file,
                dry_run=dry_run,
                feature_count=0,
                created=[],
                skipped=[],
                warnings=warnings,
            )
            click.echo(json.dumps(payload, indent=2))
            return

        for warning in warnings:
            _print_warning(warning)
        click.echo("Expected locations:")
        for path in SUGGESTED_PRD_LOCATIONS:
            click.echo(f"  - {path}")
        click.echo("Nothing to plan yet.")
        return

    titles, title_warnings = _extract_feature_titles(prd_content)
    warnings.extend(title_warnings)
    features_dir = Path("features")

    if not titles:
        titles = ["PRD"]

    created, skipped = _apply_plan(
        titles,
        features_dir=features_dir,
        dry_run=dry_run,
    )
    feature_count = len(titles)

    if format_type == "json":
        payload = _build_plan_payload(
            prd_path=prd_file,
            dry_run=dry_run,
            feature_count=feature_count,
            created=created,
            skipped=skipped,
            warnings=warnings,
        )
        click.echo(json.dumps(payload, indent=2))
        return

    for warning in warnings:
        _print_warning(warning)
    _print_plan_summary(feature_count=feature_count, dry_run=dry_run)
    _print_plan_results(created=created, skipped=skipped, dry_run=dry_run)
