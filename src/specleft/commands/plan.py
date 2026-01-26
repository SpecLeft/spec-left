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
    h2_titles = [
        line[3:].strip()
        for line in lines
        if line.startswith("## ") and "feature" in line.lower()
    ]

    if h2_titles:
        return [title for title in h2_titles if title], warnings

    if len(h1_titles) == 1 and h1_titles[0]:
        warnings.append("No secondary headings found; using top-level title.")
        return [h1_titles[0]], warnings

    warnings.append("No usable headings found; creating features/prd.md.")
    return [], warnings


def _extract_prd_scenarios(
    prd_content: str,
    *,
    require_step_keywords: bool = True,
) -> tuple[
    dict[str, list[dict[str, object]]],
    list[dict[str, object]],
    dict[str, str],
    list[str],
]:
    warnings: list[str] = []
    scenarios_by_feature: dict[str, list[dict[str, object]]] = {}
    orphan_scenarios: list[dict[str, object]] = []
    feature_priorities: dict[str, str] = {}

    def parse_heading(line: str) -> tuple[int, str] | None:
        stripped = line.lstrip()
        if not stripped.startswith("#"):
            return None
        level = len(stripped) - len(stripped.lstrip("#"))
        if level < 2 or level > 4:
            return None
        if len(stripped) <= level or stripped[level] != " ":
            return None
        return level, stripped[level + 1 :].strip()

    def is_feature_heading(level: int, text: str) -> bool:
        return level == 2 and text.lower().startswith("feature")

    def extract_scenario_title(text: str) -> str | None:
        lower = text.lower()
        marker = "scenario:"
        if marker not in lower:
            return None
        start = lower.find(marker) + len(marker)
        title = text[start:].strip()
        return title or "Scenario"

    def is_step_line(text: str) -> bool:
        lowered = text.lower()
        return lowered.startswith(("given ", "when ", "then ", "and ", "but "))

    def normalize_step(text: str) -> str | None:
        stripped = text.strip()
        if not stripped:
            return None
        if require_step_keywords and not is_step_line(stripped):
            return None
        return stripped

    def extract_steps(lines: list[str]) -> list[str]:
        steps: list[str] = []
        for raw in lines:
            stripped = raw.strip()
            if not stripped:
                continue
            if stripped.startswith(("-", "*", "•")):
                candidate = stripped[1:].strip()
            else:
                candidate = stripped
            normalized = normalize_step(candidate)
            if normalized:
                steps.append(normalized)
        return steps

    def extract_priority(line: str) -> str | None:
        stripped = line.strip()
        if stripped.startswith("-"):
            stripped = stripped[1:].strip()
        lower = stripped.lower()
        if not lower.startswith("priority:"):
            return None
        value = stripped.split(":", 1)[1].strip()
        return value or None

    lines = prd_content.splitlines()
    current_feature: str | None = None
    index = 0
    while index < len(lines):
        line = lines[index]
        heading = parse_heading(line)
        if heading:
            level, text = heading
            if is_feature_heading(level, text):
                current_feature = text
            scenario_title = extract_scenario_title(text)
            if scenario_title:
                block_lines: list[str] = []
                index += 1
                while index < len(lines):
                    next_heading = parse_heading(lines[index])
                    if next_heading:
                        break
                    block_lines.append(lines[index])
                    index += 1
                steps = extract_steps(block_lines)
                scenario_priority = None
                for block_line in block_lines:
                    scenario_priority = extract_priority(block_line)
                    if scenario_priority:
                        break
                scenario: dict[str, object] = {
                    "title": scenario_title,
                    "steps": steps,
                }
                if scenario_priority:
                    scenario["priority"] = scenario_priority
                if current_feature is None:
                    warnings.append(
                        f" Scenario found without feature - '{scenario_title}'. "
                    )
                    orphan_scenarios.append(scenario)
                else:
                    scenarios_by_feature.setdefault(current_feature, []).append(
                        scenario
                    )
                continue
        if current_feature is not None and current_feature not in feature_priorities:
            priority_value = extract_priority(line)
            if priority_value:
                feature_priorities[current_feature] = priority_value
        index += 1

    return scenarios_by_feature, orphan_scenarios, feature_priorities, warnings


def _render_scenarios(scenarios: list[dict[str, object]]) -> str:
    blocks: list[str] = []
    for scenario in scenarios:
        title = str(scenario.get("title", "Scenario"))
        priority = scenario.get("priority")
        steps_value = scenario.get("steps")
        steps: list[str] = []
        if isinstance(steps_value, list):
            steps = [str(step) for step in steps_value]
        step_lines = [f"- {step}" for step in steps]
        block = "\n".join(
            [
                f"### Scenario: {title}",
                f"priority: {priority}" if priority else "",
                *step_lines,
            ]
        ).strip()
        blocks.append(block)
    return "\n\n".join(blocks).strip()


def _feature_template(
    title: str,
    scenarios: list[dict[str, object]] | None = None,
    priority: str | None = None,
) -> str:
    scenario_block = None
    if scenarios:
        rendered = _render_scenarios(scenarios)
        if rendered:
            scenario_block = rendered
    default_block = textwrap.dedent(
        """
        ### Scenario: Example
        priority: medium

        - Given a precondition
        - When an action occurs
        - Then the expected result
        """
    ).strip()
    block = scenario_block or default_block
    return "\n".join(
        [
            f"# {title}",
            "",
            f"priority: {priority}" if priority else "",
            "" if priority else "",
            "## Scenarios",
            "",
            block,
            "",
        ]
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
    scenarios_by_feature: dict[str, list[dict[str, object]]] | None = None,
    feature_priorities: dict[str, str] | None = None,
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
        scenarios = None
        if scenarios_by_feature:
            scenarios = scenarios_by_feature.get(title)
        priority = None
        if feature_priorities:
            priority = feature_priorities.get(title)
        path.write_text(
            _feature_template(title, scenarios=scenarios, priority=priority)
        )
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
    orphan_scenarios: list[dict[str, object]] | None = None,
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
    payload["oprhan_scenarios"] = orphan_scenarios or []
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
    (
        scenarios_by_feature,
        orphan_scenarios,
        feature_priorities,
        scenario_warnings,
    ) = _extract_prd_scenarios(prd_content, require_step_keywords=True)
    warnings.extend(scenario_warnings)
    features_dir = Path("features")

    if not titles:
        titles = ["PRD"]

    created, skipped = _apply_plan(
        titles,
        features_dir=features_dir,
        dry_run=dry_run,
        scenarios_by_feature=scenarios_by_feature,
        feature_priorities=feature_priorities,
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
            orphan_scenarios=orphan_scenarios,
        )
        click.echo(json.dumps(payload, indent=2))
        return

    for warning in warnings:
        _print_warning(warning)
    _print_plan_summary(feature_count=feature_count, dry_run=dry_run)
    _print_plan_results(created=created, skipped=skipped, dry_run=dry_run)
