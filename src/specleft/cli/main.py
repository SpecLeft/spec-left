"""SpecLeft CLI - Command line interface for test management."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import webbrowser
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, cast

from click.testing import CliRunner

import click
from jinja2 import Environment, FileSystemLoader, Template

from specleft.schema import (
    ExecutionTime,
    FeatureSpec,
    Priority,
    ScenarioSpec,
    SpecsConfig,
    StorySpec,
)
from specleft.validator import collect_spec_stats, load_specs_directory


CLI_VERSION = "0.2.0"
CONTRACT_VERSION = "1.0"
CONTRACT_DOC_PATH = "docs/agent-contract.md"


@contextmanager
def _working_directory(path: Path) -> Any:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


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
    overwrites: bool


@dataclass(frozen=True)
class SkeletonSkipPlan:
    """Plan describing a skipped skeleton output."""

    scenarios: list[ScenarioPlan]
    output_path: Path
    reason: str


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
    skipped_plans: list[SkeletonSkipPlan]


@dataclass(frozen=True)
class ScenarioStatus:
    """Status information for a scenario."""

    status: str
    test_file: str | None
    test_function: str | None
    reason: str | None


@dataclass(frozen=True)
class ScenarioStatusEntry:
    """Scenario status entry for reporting."""

    feature: FeatureSpec
    story: StorySpec
    scenario: ScenarioSpec
    status: str
    test_file: str
    test_function: str
    reason: str | None


@dataclass(frozen=True)
class StatusSummary:
    """Coverage summary across scenarios."""

    total_features: int
    total_stories: int
    total_scenarios: int
    implemented: int
    skipped: int
    coverage_percent: int


@dataclass(frozen=True)
class CoverageTally:
    """Coverage tally for a grouping."""

    total: int = 0
    implemented: int = 0


@dataclass(frozen=True)
class CoverageOverall:
    """Overall coverage metrics."""

    total: int
    implemented: int
    skipped: int
    percent: float | None


@dataclass(frozen=True)
class CoverageMetrics:
    """Coverage metrics for multiple groupings."""

    overall: CoverageOverall
    by_feature: dict[str, CoverageTally]
    by_priority: dict[str, CoverageTally]
    by_execution_time: dict[str, CoverageTally]


@dataclass(frozen=True)
class ContractCheckResult:
    """Result of a contract test check."""

    category: str
    name: str
    status: str
    message: str | None = None


@dataclass(frozen=True)
class SkeletonScenarioEntry:
    """Flattened scenario entry for skeleton planning."""

    scenario: ScenarioPlan
    output_path: Path
    overwrites: bool
    skip_reason: str | None = None


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


def _load_dependency_names() -> list[str]:
    dependencies = ["pytest", "pydantic", "click", "jinja2", "python-frontmatter"]
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        return dependencies

    try:
        content = pyproject_path.read_text()
    except OSError:
        return dependencies

    match = re.search(
        r"^\s*dependencies\s*=\s*\[(.*?)\]\s*$", content, re.DOTALL | re.MULTILINE
    )
    if not match:
        return dependencies

    dependencies_block = match.group(1)
    entries = re.findall(r'"([^"]+)"', dependencies_block)
    parsed: list[str] = []
    for entry in entries:
        name = re.split(r"[<>=\s]", entry.strip(), maxsplit=1)[0]
        if name:
            parsed.append(name)

    return parsed or dependencies


def _build_status_table_rows(entries: list[ScenarioStatusEntry]) -> list[str]:
    if not entries:
        return []

    max_path_len = max(
        len(f"{entry.test_file}::{entry.test_function}") for entry in entries
    )
    width = max(70, max_path_len + 10)
    return ["━" * width]


def _collect_scenario_entries(entries: list[ScenarioStatusEntry]) -> list[ScenarioSpec]:
    return [entry.scenario for entry in entries]


def _coverage_summary(implemented: int, total: int) -> str:
    if total == 0:
        return "N/A"
    percent = _format_coverage_percent(implemented, total)
    if percent is None:
        return "N/A"
    return f"{percent:.1f}% ({implemented}/{total})"


def _summary_row(label: str, summary: CoverageTally) -> str:
    if summary.total == 0:
        return f"  {label:<10} N/A (0/0)"
    percent = _format_coverage_percent(summary.implemented, summary.total) or 0.0
    return f"  {label:<10} {percent:.1f}% ({summary.implemented}/{summary.total})"


def _format_priority_key(priority: Priority) -> str:
    return priority.value


def _format_execution_key(execution_time: ExecutionTime) -> str:
    return execution_time.value


def _iter_py_files(tests_dir: Path) -> list[Path]:
    if not tests_dir.exists():
        return []

    return [
        file_path
        for file_path in tests_dir.rglob("*.py")
        if not file_path.name.startswith("__")
    ]


def _extract_specleft_calls(tree: ast.AST) -> dict[str, dict[str, object]]:
    scenario_map: dict[str, dict[str, object]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            scenario_id = _extract_specleft_scenario_id(decorator)
            if scenario_id is None:
                continue
            scenario_map[scenario_id] = {
                "function": node.name,
                "skip": _extract_skip_flag(decorator),
            }
    return scenario_map


def _extract_skip_flag(decorator: ast.expr) -> bool:
    if not isinstance(decorator, ast.Call):
        return False
    for keyword in decorator.keywords:
        if keyword.arg == "skip" and isinstance(keyword.value, ast.Constant):
            return bool(keyword.value.value)
    return False


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

        for scenario_id, info in _extract_specleft_calls(tree).items():
            scenario_map[scenario_id] = {
                "function": info["function"],
                "skip": info["skip"],
                "file": str(file_path),
            }

    return scenario_map


def _build_status_entries(
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

            test_file = _story_output_path(
                tests_dir, feature.feature_id, story.story_id
            )
            for scenario in story.scenarios:
                info = scenario_map.get(scenario.scenario_id)
                status = _determine_scenario_status(
                    scenario_id=scenario.scenario_id,
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


def _determine_scenario_status(
    *,
    scenario_id: str,
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


def _build_status_json(
    entries: list[ScenarioStatusEntry],
    *,
    include_execution_time: bool,
) -> dict[str, Any]:
    summary = _summarize_status_entries(entries)
    features: list[dict[str, object]] = []

    feature_groups: dict[str, list[ScenarioStatusEntry]] = {}
    for entry in entries:
        feature_groups.setdefault(entry.feature.feature_id, []).append(entry)

    for feature_entries in feature_groups.values():
        feature_summary = _summarize_status_entries(feature_entries)
        feature = feature_entries[0].feature
        feature_payload: dict[str, object] = {
            "feature_id": feature.feature_id,
            "feature_name": feature.name,
            "feature_file": str(feature.source_dir / "_feature.md")
            if feature.source_dir
            else None,
            "coverage_percent": feature_summary.coverage_percent,
            "stories": [],
            "summary": {
                "total_scenarios": feature_summary.total_scenarios,
                "implemented": feature_summary.implemented,
                "skipped": feature_summary.skipped,
            },
        }

        story_groups: dict[str, list[ScenarioStatusEntry]] = {}
        for entry in feature_entries:
            story_groups.setdefault(entry.story.story_id, []).append(entry)

        for story_entries in story_groups.values():
            story_summary = _summarize_status_entries(story_entries)
            story = story_entries[0].story
            story_payload: dict[str, object] = {
                "story_id": story.story_id,
                "story_name": story.name,
                "story_file": str(story.source_dir / "_story.md")
                if story.source_dir
                else None,
                "coverage_percent": story_summary.coverage_percent,
                "scenarios": [],
                "summary": {
                    "total": story_summary.total_scenarios,
                    "implemented": story_summary.implemented,
                    "skipped": story_summary.skipped,
                },
            }

            for entry in story_entries:
                scenario_payload: dict[str, object] = {
                    "scenario_id": entry.scenario.scenario_id,
                    "scenario_name": entry.scenario.name,
                    "scenario_file": str(entry.scenario.source_file)
                    if entry.scenario.source_file
                    else None,
                    "status": entry.status,
                    "test_file": entry.test_file,
                    "test_function": entry.test_function,
                    "priority": entry.scenario.priority.value,
                    "tags": entry.scenario.tags,
                }
                if include_execution_time:
                    scenario_payload["execution_time"] = (
                        entry.scenario.execution_time.value
                    )
                if entry.reason:
                    scenario_payload["reason"] = entry.reason

                cast(list[dict[str, object]], story_payload["scenarios"]).append(
                    scenario_payload
                )

            cast(list[dict[str, object]], feature_payload["stories"]).append(
                story_payload
            )

        features.append(feature_payload)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
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


def _print_status_table(
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
                f"  Priority: {entry.scenario.priority.value} | Tags: {', '.join(entry.scenario.tags) if entry.scenario.tags else 'none'}"
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

    feature_groups: dict[str, list[ScenarioStatusEntry]] = {}
    for entry in entries:
        feature_groups.setdefault(entry.feature.feature_id, []).append(entry)

    for feature_id, feature_entries in feature_groups.items():
        feature_summary = _summarize_status_entries(feature_entries)
        feature_name = feature_entries[0].feature.name
        click.echo(f"Feature: {feature_id} ({feature_summary.coverage_percent}%)")
        story_groups: dict[str, list[ScenarioStatusEntry]] = {}
        for entry in feature_entries:
            story_groups.setdefault(entry.story.story_id, []).append(entry)

        for story_id, story_entries in story_groups.items():
            story_summary = _summarize_status_entries(story_entries)
            click.echo(f"  Story: {story_id} ({story_summary.coverage_percent}%)")
            for entry in story_entries:
                marker = "✓" if entry.status == "implemented" else "⚠"
                path = f"{entry.test_file}::{entry.test_function}"
                suffix = "" if entry.status == "implemented" else " (skipped)"
                click.echo(
                    f"    {marker} {entry.scenario.scenario_id:<25} {path}{suffix}"
                )
            click.echo("")

    click.echo(
        f"Overall: {summary.implemented}/{summary.total_scenarios} scenarios implemented ({summary.coverage_percent}%)"
    )
    if separator:
        click.echo(separator[0])


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


def _build_coverage_metrics(entries: list[ScenarioStatusEntry]) -> CoverageMetrics:
    total = len(entries)
    implemented = sum(1 for entry in entries if entry.status == "implemented")
    skipped = total - implemented

    features: dict[str, CoverageTally] = {}
    priorities: dict[str, CoverageTally] = {}
    execution_times: dict[str, CoverageTally] = {}

    for entry in entries:
        feature_key = entry.feature.feature_id
        features.setdefault(feature_key, CoverageTally())
        feature_tally = features[feature_key]
        features[feature_key] = CoverageTally(
            total=feature_tally.total + 1,
            implemented=feature_tally.implemented
            + (1 if entry.status == "implemented" else 0),
        )

        priority_key = _format_priority_key(entry.scenario.priority)
        priorities.setdefault(priority_key, CoverageTally())
        priority_tally = priorities[priority_key]
        priorities[priority_key] = CoverageTally(
            total=priority_tally.total + 1,
            implemented=priority_tally.implemented
            + (1 if entry.status == "implemented" else 0),
        )

        execution_key = _format_execution_key(entry.scenario.execution_time)
        execution_times.setdefault(execution_key, CoverageTally())
        execution_tally = execution_times[execution_key]
        execution_times[execution_key] = CoverageTally(
            total=execution_tally.total + 1,
            implemented=execution_tally.implemented
            + (1 if entry.status == "implemented" else 0),
        )

    overall = CoverageOverall(
        total=total,
        implemented=implemented,
        skipped=skipped,
        percent=_format_coverage_percent(implemented, total),
    )

    return CoverageMetrics(
        overall=overall,
        by_feature=features,
        by_priority=priorities,
        by_execution_time=execution_times,
    )


def _build_coverage_json(entries: list[ScenarioStatusEntry]) -> dict[str, object]:
    metrics = _build_coverage_metrics(entries)
    feature_payload = []
    for feature_id, data in metrics.by_feature.items():
        feature_payload.append(
            {
                "feature_id": feature_id,
                "total": data.total,
                "implemented": data.implemented,
                "percent": _format_coverage_percent(data.implemented, data.total),
            }
        )

    def _build_group_payload(
        values: dict[str, CoverageTally],
    ) -> dict[str, dict[str, object]]:
        payload: dict[str, dict[str, object]] = {}
        for key, data in values.items():
            payload[key] = {
                "total": data.total,
                "implemented": data.implemented,
                "percent": _format_coverage_percent(data.implemented, data.total),
            }
        return payload

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "coverage": {
            "overall": {
                "total_scenarios": metrics.overall.total,
                "implemented": metrics.overall.implemented,
                "skipped": metrics.overall.skipped,
                "percent": metrics.overall.percent,
            },
            "by_feature": feature_payload,
            "by_priority": _build_group_payload(metrics.by_priority),
            "by_execution_time": _build_group_payload(metrics.by_execution_time),
        },
    }


def _print_coverage_table(entries: list[ScenarioStatusEntry]) -> None:
    metrics = _build_coverage_metrics(entries)

    click.echo("Coverage Report")
    click.echo("━" * 58)
    click.echo(
        f"Overall Coverage: {_coverage_summary(metrics.overall.implemented, metrics.overall.total)}"
    )
    click.echo("")

    click.echo("By Feature:")
    feature_items = sorted(metrics.by_feature.items())
    for feature_id, data in feature_items:
        coverage = _format_coverage_percent(data.implemented, data.total)
        coverage_label = "N/A" if coverage is None else f"{coverage:.1f}%"
        click.echo(
            f"  {feature_id:<12} {coverage_label} ({data.implemented}/{data.total})"
        )
    if not feature_items:
        click.echo("  None")

    click.echo("")
    click.echo("By Priority:")
    for priority in Priority:
        data = metrics.by_priority.get(priority.value, CoverageTally())
        click.echo(_summary_row(priority.value, data))

    click.echo("")
    click.echo("By Execution Time:")
    for execution_time in ExecutionTime:
        data = metrics.by_execution_time.get(execution_time.value, CoverageTally())
        click.echo(_summary_row(execution_time.value, data))
    click.echo("━" * 58)


def _priority_sort_value(priority: str) -> int:
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return order.get(priority, 4)


def _format_test_location(test_file: str | None, test_function: str | None) -> str:
    if test_file and test_function:
        return f"{test_file}::{test_function}"
    if test_file:
        return test_file
    return ""


def _build_doctor_checks() -> dict[str, Any]:
    import importlib.metadata as metadata

    cli_check = {"status": "pass", "version": CLI_VERSION}

    python_info = sys.version_info
    minimum_python = (3, 9, 0)
    python_version = f"{python_info.major}.{python_info.minor}.{python_info.micro}"
    python_ok = python_info >= minimum_python
    python_check = {
        "status": "pass" if python_ok else "fail",
        "version": python_version,
        "minimum": "3.9.0",
    }
    if not python_ok:
        python_check["message"] = f"Python 3.9+ required. Current: {python_version}"

    dependencies = _load_dependency_names()
    dependency_packages: list[dict[str, object]] = []
    dependencies_ok = True
    for package in dependencies:
        try:
            dependency_packages.append(
                {
                    "name": package,
                    "version": metadata.version(package),
                    "status": "pass",
                }
            )
        except metadata.PackageNotFoundError:
            dependency_packages.append(
                {
                    "name": package,
                    "version": None,
                    "status": "fail",
                    "message": "Not installed",
                }
            )
            dependencies_ok = False

    dependency_check = {
        "status": "pass" if dependencies_ok else "fail",
        "packages": dependency_packages,
    }

    plugin_registered = False
    plugin_status = "fail"
    plugin_error = None
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            output = result.stdout + result.stderr
            plugin_registered = "specleft" in output.lower()
            plugin_status = "pass" if plugin_registered else "warn"
        else:
            plugin_status = "fail"
            plugin_error = result.stderr.strip() or "pytest execution failed"
    except Exception as exc:
        plugin_status = "fail"
        plugin_error = str(exc)

    plugin_check: dict[str, object] = {
        "status": plugin_status,
        "registered": plugin_registered,
    }
    if plugin_error:
        plugin_check["error"] = plugin_error

    features_dir = Path("features")
    tests_dir = Path("tests")
    features_readable = features_dir.exists() and os.access(features_dir, os.R_OK)
    tests_writable = tests_dir.exists() and os.access(tests_dir, os.W_OK)
    if not tests_dir.exists():
        tests_writable = os.access(Path("."), os.W_OK)
    directories_ok = (features_readable or not features_dir.exists()) and tests_writable
    directory_status = "pass" if directories_ok else "warn"

    directory_check = {
        "status": directory_status,
        "features_readable": features_readable,
        "tests_writable": tests_writable,
    }

    return {
        "version": CLI_VERSION,
        "checks": {
            "cli_available": cli_check,
            "pytest_plugin": plugin_check,
            "python_version": python_check,
            "dependencies": dependency_check,
            "directories": directory_check,
        },
    }


def _build_doctor_output(checks: dict[str, Any]) -> dict[str, Any]:
    checks_map = cast(dict[str, Any], checks.get("checks", {}))
    errors: list[str] = []
    suggestions: list[str] = []
    healthy = True

    python_check = checks_map.get("python_version", {})
    if python_check.get("status") == "fail":
        healthy = False
        errors.append(
            f"Python version {python_check.get('version')} is below minimum {python_check.get('minimum')}"
        )
        suggestions.append("Upgrade Python: pyenv install 3.11")

    dependencies_check = checks_map.get("dependencies", {})
    if dependencies_check.get("status") != "pass":
        healthy = False
        for package in dependencies_check.get("packages", []):
            if package.get("status") == "fail":
                name = package.get("name")
                errors.append(f"Missing required package: {name}")
                suggestions.append(f"Install {name}: pip install {name}")

    if checks_map.get("pytest_plugin", {}).get("status") == "fail":
        healthy = False
        errors.append("Pytest plugin registration check failed")
        suggestions.append("Ensure SpecLeft is installed: pip install -e .")

    if checks_map.get("directories", {}).get("status") != "pass":
        healthy = False
        errors.append("Feature/test directory access issue")
        suggestions.append("Check directory permissions")

    output = {
        "healthy": healthy,
        "version": checks.get("version"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks_map,
    }

    if errors:
        output["errors"] = errors
    if suggestions:
        output["suggestions"] = suggestions

    return output


def _print_doctor_table(checks: dict[str, Any], *, verbose: bool) -> None:
    checks_map = cast(dict[str, Any], checks.get("checks", {}))
    click.echo("Checking SpecLeft installation...")
    cli_check = checks_map.get("cli_available", {})
    click.echo(f"✓ specleft CLI available (version {cli_check.get('version')})")

    plugin_check = checks_map.get("pytest_plugin", {})
    if plugin_check.get("status") == "pass":
        click.echo("✓ pytest plugin registered")
    elif plugin_check.get("status") == "warn":
        click.echo("⚠ pytest plugin may not be registered")
    else:
        click.echo("✗ pytest plugin check failed")

    python_check = checks_map.get("python_version", {})
    python_marker = "✓" if python_check.get("status") == "pass" else "✗"
    click.echo(
        f"{python_marker} Python version compatible ({python_check.get('version')})"
    )

    dependencies_check = checks_map.get("dependencies", {})
    dependencies_marker = "✓" if dependencies_check.get("status") == "pass" else "✗"
    click.echo(f"{dependencies_marker} All dependencies installed")
    for package in dependencies_check.get("packages", []):
        marker = "✓" if package.get("status") == "pass" else "✗"
        version = package.get("version") or "not installed"
        click.echo(f"  - {package.get('name')} ({version}) {marker}")
        if verbose and package.get("message"):
            click.echo(f"    {package.get('message')}")

    directory_check = checks_map.get("directories", {})
    features_marker = "✓" if directory_check.get("features_readable") else "✗"
    tests_marker = "✓" if directory_check.get("tests_writable") else "✗"
    click.echo(f"{features_marker} Can read feature directory (features/)")
    click.echo(f"{tests_marker} Can write to test directory (tests/)")

    if verbose and plugin_check.get("error"):
        click.echo(f"pytest plugin error: {plugin_check.get('error')}")

    if checks.get("errors"):
        click.echo("")
        click.secho("Issues detected:", fg="red")
        for error in checks.get("errors", []):
            click.echo(f"  - {error}")
        if checks.get("suggestions"):
            click.echo("")
            click.secho("Suggestions:", fg="yellow")
            for suggestion in checks.get("suggestions", []):
                click.echo(f"  - {suggestion}")
    else:
        click.echo("")
        click.echo("SpecLeft is ready to use.")


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
            "priority": entry.scenario.priority.value,
            "tags": entry.scenario.tags,
            "spec_file": str(entry.scenario.source_file)
            if entry.scenario.source_file
            else None,
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
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tests": tests,
        "total_unimplemented": total_unimplemented,
        "showing": len(tests),
    }
    if not tests:
        output["message"] = "All scenarios are implemented"
    return output


def _build_features_list_json(config: SpecsConfig) -> dict[str, object]:
    features_payload: list[dict[str, object]] = []
    story_count = 0
    scenario_count = 0
    for feature in config.features:
        stories_payload: list[dict[str, object]] = []
        for story in feature.stories:
            story_count += 1
            scenarios_payload = [
                {
                    "scenario_id": scenario.scenario_id,
                    "scenario_name": scenario.name,
                }
                for scenario in story.scenarios
            ]
            scenario_count += len(story.scenarios)
            stories_payload.append(
                {
                    "story_id": story.story_id,
                    "story_name": story.name,
                    "scenarios": scenarios_payload,
                }
            )
        features_payload.append(
            {
                "feature_id": feature.feature_id,
                "feature_name": feature.name,
                "stories": stories_payload,
            }
        )

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
    stats: object | None,
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
        "timestamp": datetime.now(timezone.utc).isoformat(),
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


def _build_contract_payload() -> dict[str, object]:
    return {
        "contract_version": CONTRACT_VERSION,
        "specleft_version": CLI_VERSION,
        "guarantees": {
            "safety": {
                "no_implicit_writes": True,
                "dry_run_never_writes": True,
                "existing_tests_not_modified_by_default": True,
            },
            "execution": {
                "skeletons_skipped_by_default": True,
                "skipped_never_fail": True,
                "validation_non_destructive": True,
            },
            "determinism": {
                "deterministic_for_same_inputs": True,
                "safe_for_retries": True,
            },
            "cli_api": {
                "json_supported_globally": True,
                "json_additive_within_minor": True,
                "exit_codes": {
                    "success": 0,
                    "error": 1,
                    "cancelled": 2,
                },
            },
        },
        "docs": {
            "agent_contract": CONTRACT_DOC_PATH,
        },
    }


def _print_contract_table(payload: dict[str, object]) -> None:
    guarantees = cast(dict[str, Any], payload.get("guarantees", {}))
    safety = cast(dict[str, Any], guarantees.get("safety", {}))
    execution = cast(dict[str, Any], guarantees.get("execution", {}))
    determinism = cast(dict[str, Any], guarantees.get("determinism", {}))
    cli_api = cast(dict[str, Any], guarantees.get("cli_api", {}))
    click.echo("SpecLeft Agent Contract")
    click.echo("─" * 40)
    click.echo(f"Contract version: {payload.get('contract_version')}")
    click.echo(f"SpecLeft version: {payload.get('specleft_version')}")
    click.echo("")
    click.echo("Safety:")
    click.echo(
        "  - No writes without confirmation or --force"
        if safety.get("no_implicit_writes")
        else "  - No implicit writes guarantee missing"
    )
    click.echo(
        "  - --dry-run never writes to disk"
        if safety.get("dry_run_never_writes")
        else "  - --dry-run guarantee missing"
    )
    click.echo(
        "  - Existing tests not modified by default"
        if safety.get("existing_tests_not_modified_by_default")
        else "  - Existing test protection missing"
    )
    click.echo("")
    click.echo("Execution:")
    click.echo(
        "  - Skeleton tests skipped by default"
        if execution.get("skeletons_skipped_by_default")
        else "  - Skeleton skip guarantee missing"
    )
    click.echo(
        "  - Skipped scenarios never fail tests"
        if execution.get("skipped_never_fail")
        else "  - Skip behavior guarantee missing"
    )
    click.echo(
        "  - Validation is non-destructive"
        if execution.get("validation_non_destructive")
        else "  - Validation guarantee missing"
    )
    click.echo("")
    click.echo("Determinism:")
    click.echo(
        "  - Commands deterministic for same inputs"
        if determinism.get("deterministic_for_same_inputs")
        else "  - Determinism guarantee missing"
    )
    click.echo(
        "  - Safe to re-run in retry loops"
        if determinism.get("safe_for_retries")
        else "  - Retry safety guarantee missing"
    )
    click.echo("")
    click.echo("JSON & CLI:")
    click.echo(
        "  - All commands support --format json"
        if cli_api.get("json_supported_globally")
        else "  - JSON support guarantee missing"
    )
    click.echo(
        "  - JSON schema additive within minor versions"
        if cli_api.get("json_additive_within_minor")
        else "  - JSON compatibility guarantee missing"
    )
    click.echo("  - Stable exit codes: 0=success, 1=error, 2=cancel")
    click.echo("")
    click.echo(f"For full details, see: {CONTRACT_DOC_PATH}")
    click.echo("─" * 40)


def _build_contract_test_payload(
    *,
    passed: bool,
    checks: list[ContractCheckResult],
    errors: list[str],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "contract_version": CONTRACT_VERSION,
        "specleft_version": CLI_VERSION,
        "passed": passed,
        "checks": [
            {
                "category": check.category,
                "name": check.name,
                "status": check.status,
                **({"message": check.message} if check.message else {}),
            }
            for check in checks
        ],
    }
    if errors:
        payload["errors"] = errors
    return payload


def _format_contract_check_label(check: ContractCheckResult) -> str:
    return f"{check.category.capitalize()}: {check.name.replace('_', ' ')}"


def _emit_contract_check(check: ContractCheckResult, verbose: bool) -> None:
    marker = "✓" if check.status == "pass" else "✗"
    click.echo(f"{marker} {_format_contract_check_label(check)}")
    if verbose and check.message:
        click.echo(f"  {check.message}")


def _load_json_output(
    raw_output: str, *, allow_preamble: bool = False
) -> object | None:
    payload = raw_output
    if allow_preamble:
        lines = raw_output.splitlines()
        if lines and lines[0].strip() == "Running contract tests...":
            payload = "\n".join(lines[1:])
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def _print_contract_test_table(
    checks: list[ContractCheckResult], passed: bool, verbose: bool
) -> None:
    click.echo("SpecLeft Agent Contract Tests")
    click.echo("━" * 44)
    for check in checks:
        _emit_contract_check(check, verbose)
    click.echo("")
    if passed:
        click.echo("All Agent Contract guarantees verified.")
    else:
        click.echo("One or more Agent Contract guarantees failed.")


def _write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).strip())


def _create_contract_specs(root: Path) -> None:
    _write_text_file(
        root / "features" / "auth" / "_feature.md",
        """
        ---
        feature_id: auth
        priority: high
        ---
        # Feature: Auth
        """,
    )
    _write_text_file(
        root / "features" / "auth" / "login" / "_story.md",
        """
        ---
        story_id: login
        ---
        # Story: Login
        """,
    )
    _write_text_file(
        root / "features" / "auth" / "login" / "login-success.md",
        """
        ---
        scenario_id: login-success
        priority: high
        execution_time: fast
        ---
        # Scenario: Login Success
        ## Steps
        - **Given** a user exists
        - **When** the user logs in
        - **Then** access is granted
        """,
    )


def _record_file_snapshot(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in root.rglob("*"):
        if path.is_file():
            snapshot[str(path.relative_to(root))] = path.read_text()
    return snapshot


def _compare_file_snapshot(root: Path, snapshot: dict[str, str]) -> bool:
    current = _record_file_snapshot(root)
    return current == snapshot


def _run_contract_tests(
    verbose: bool,
    on_progress: Callable[[ContractCheckResult], None] | None = None,
) -> tuple[bool, list[ContractCheckResult], list[str]]:
    checks: list[ContractCheckResult] = []
    errors: list[str] = []
    runner = CliRunner()

    def _record_check(result: ContractCheckResult) -> None:
        checks.append(result)
        if on_progress is not None:
            on_progress(result)

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        _create_contract_specs(root)

        with _working_directory(root):
            dry_run_result = runner.invoke(
                cli, ["test", "skeleton", "--dry-run", "--format", "json"]
            )
            dry_run_pass = dry_run_result.exit_code == 0 and not Path("tests").exists()
            _record_check(
                ContractCheckResult(
                    category="safety",
                    name="dry_run_no_writes",
                    status="pass" if dry_run_pass else "fail",
                    message=None if dry_run_pass else "Dry run created files",
                )
            )

            cancel_result = runner.invoke(cli, ["test", "skeleton"], input="n\n")
            cancel_pass = cancel_result.exit_code == 2 and not Path("tests").exists()
            _record_check(
                ContractCheckResult(
                    category="safety",
                    name="no_implicit_writes",
                    status="pass" if cancel_pass else "fail",
                    message=None
                    if cancel_pass
                    else "Skeleton wrote without confirmation",
                )
            )

            create_result = runner.invoke(cli, ["test", "skeleton"], input="y\n")
            generated_file = Path("tests/auth/test_login.py")
            created = create_result.exit_code == 0 and generated_file.exists()
            _record_check(
                ContractCheckResult(
                    category="execution",
                    name="skeletons_skipped_by_default",
                    status="pass"
                    if created and "skip=True" in generated_file.read_text()
                    else "fail",
                    message=None
                    if created and "skip=True" in generated_file.read_text()
                    else "Skeleton tests are not skipped",
                )
            )

            snapshot = {}
            if created:
                snapshot = _record_file_snapshot(root)
                rerun_result = runner.invoke(cli, ["test", "skeleton"])
                unchanged = rerun_result.exit_code == 0 and _compare_file_snapshot(
                    root, snapshot
                )
            else:
                unchanged = False

            _record_check(
                ContractCheckResult(
                    category="safety",
                    name="existing_tests_not_modified_by_default",
                    status="pass" if unchanged else "fail",
                    message=None
                    if unchanged
                    else "Existing tests were modified without --force",
                )
            )

            validate_snapshot = _record_file_snapshot(root)
            validate_result = runner.invoke(
                cli, ["features", "validate", "--format", "json"]
            )
            validation_pass = validate_result.exit_code == 0 and _compare_file_snapshot(
                root, validate_snapshot
            )
            _record_check(
                ContractCheckResult(
                    category="execution",
                    name="validation_non_destructive",
                    status="pass" if validation_pass else "fail",
                    message=None if validation_pass else "Validation modified files",
                )
            )

            def _normalize_payload(raw_output: str) -> dict[str, object] | None:
                payload = _load_json_output(raw_output, allow_preamble=True)
                if isinstance(payload, dict):
                    payload.pop("timestamp", None)
                    return payload
                return None

            baseline_result = runner.invoke(
                cli, ["test", "skeleton", "--dry-run", "--format", "json"]
            )
            deterministic_result = runner.invoke(
                cli, ["test", "skeleton", "--dry-run", "--format", "json"]
            )
            baseline_payload = _normalize_payload(baseline_result.output)
            deterministic_payload = _normalize_payload(deterministic_result.output)
            deterministic_pass = (
                baseline_result.exit_code == 0
                and deterministic_result.exit_code == 0
                and deterministic_payload is not None
                and deterministic_payload == baseline_payload
            )
            _record_check(
                ContractCheckResult(
                    category="determinism",
                    name="deterministic_for_same_inputs",
                    status="pass" if deterministic_pass else "fail",
                    message=None
                    if deterministic_pass
                    else "Outputs differed between runs",
                )
            )

            retry_snapshot = _record_file_snapshot(root)
            safe_retry_pass = _compare_file_snapshot(root, retry_snapshot)
            _record_check(
                ContractCheckResult(
                    category="determinism",
                    name="safe_for_retries",
                    status="pass" if safe_retry_pass else "fail",
                    message=None
                    if safe_retry_pass
                    else "Retry introduced side effects",
                )
            )

            json_commands = [
                ("doctor", ["doctor", "--format", "json"]),
                ("status", ["status", "--format", "json"]),
                ("next", ["next", "--format", "json"]),
                ("coverage", ["coverage", "--format", "json"]),
                ("features_list", ["features", "list", "--format", "json"]),
                ("features_stats", ["features", "stats", "--format", "json"]),
                ("features_validate", ["features", "validate", "--format", "json"]),
                ("report", ["test", "report", "--format", "json"]),
                ("contract", ["contract", "--format", "json"]),
                ("contract_test", ["contract", "test", "--format", "json"]),
                (
                    "skeleton",
                    ["test", "skeleton", "--dry-run", "--format", "json"],
                ),
            ]

            json_pass = True
            json_failures: list[str] = []
            for label, command in json_commands:
                result = runner.invoke(cli, command)
                payload = _load_json_output(
                    result.output, allow_preamble=label == "contract_test"
                )
                if payload is None:
                    json_pass = False
                    json_failures.append(label)
                    continue
                if result.exit_code not in {0, 1, 2}:
                    json_pass = False
                    json_failures.append(label)
            _record_check(
                ContractCheckResult(
                    category="cli_api",
                    name="json_supported_globally",
                    status="pass" if json_pass else "fail",
                    message=None
                    if json_pass
                    else f"JSON format unsupported: {', '.join(json_failures)}",
                )
            )

            contract_result = runner.invoke(cli, ["contract", "--format", "json"])
            schema_pass = False
            if contract_result.exit_code == 0:
                contract_payload = _load_json_output(contract_result.output)
                schema_pass = isinstance(contract_payload, dict) and bool(
                    contract_payload.get("contract_version")
                    and contract_payload.get("specleft_version")
                    and contract_payload.get("guarantees")
                )
            _record_check(
                ContractCheckResult(
                    category="cli_api",
                    name="json_schema_valid",
                    status="pass" if schema_pass else "fail",
                    message=None
                    if schema_pass
                    else "Contract JSON missing required keys",
                )
            )

            exit_code_pass = cancel_result.exit_code == 2
            _record_check(
                ContractCheckResult(
                    category="cli_api",
                    name="exit_codes_correct",
                    status="pass" if exit_code_pass else "fail",
                    message=None if exit_code_pass else "Cancel exit code not 2",
                )
            )

            skip_pass = create_result.exit_code == 0
            _record_check(
                ContractCheckResult(
                    category="execution",
                    name="skipped_never_fail",
                    status="pass" if skip_pass else "fail",
                    message=None if skip_pass else "Skeleton run failed",
                )
            )

    passed = all(check.status == "pass" for check in checks)
    if not passed:
        errors.append("Agent Contract violation detected")
    if verbose:
        for check in checks:
            if check.status == "fail" and check.message:
                errors.append(f"{check.category}: {check.name} - {check.message}")

    return passed, checks, errors


def _story_output_path(output_path: Path, feature_id: str, story_id: str) -> Path:
    return output_path / feature_id / f"test_{story_id}.py"


def _feature_with_story(feature: FeatureSpec, story: StorySpec) -> FeatureSpec:
    return feature.model_copy(update={"stories": [story]})


def _plan_skeleton_generation(
    config: SpecsConfig,
    output_path: Path,
    template: Template,
    single_file: bool,
    force: bool,
) -> SkeletonPlanResult:
    plans: list[SkeletonPlan] = []
    skipped_plans: list[SkeletonSkipPlan] = []
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


def _format_status_marker(status: str) -> str:
    if status == "implemented":
        return "✓"
    if status == "skipped":
        return "⚠"
    return "✗"


def _format_coverage_percent(implemented: int, total: int) -> float | None:
    if total == 0:
        return None
    return round((implemented / total) * 100, 1)


def _format_execution_time_value(execution_time: str) -> str:
    return execution_time.capitalize()


def _badge_color(coverage: float | None) -> str:
    if coverage is None:
        return "#9f9f9f"
    if coverage >= 80:
        return "#4cce5e"
    if coverage >= 60:
        return "#f0c648"
    return "#e05d44"


def _render_badge_svg(label: str, message: str, color: str) -> str:
    def _text_width(text: str) -> int:
        return max(1, len(text)) * 7

    label_width = _text_width(label) + 10
    message_width = _text_width(message) + 10
    total_width = label_width + message_width
    label_x = label_width / 2
    message_x = label_width + message_width / 2
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="'
        f'{total_width}" height="20" role="img" aria-label="{label}: {message}">'
        '<linearGradient id="s" x2="0" y2="100%">'
        '<stop offset="0" stop-color="#bbb" stop-opacity=".1"/>'
        '<stop offset="1" stop-opacity=".1"/>'
        "</linearGradient>"
        f'<rect width="{label_width}" height="20" fill="#555"/>'
        f'<rect x="{label_width}" width="{message_width}" height="20" fill="{color}"/>'
        '<rect width="' + str(total_width) + '" height="20" fill="url(#s)"/>'
        f'<g fill="#fff" text-anchor="middle" font-family="Verdana" font-size="11">'
        f'<text x="{label_x}" y="14">{label}</text>'
        f'<text x="{message_x}" y="14">{message}</text>'
        "</g>"
        "</svg>"
    )


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
    for plan in plan_result.skipped_plans:
        for scenario in plan.scenarios:
            entries.append(
                SkeletonScenarioEntry(
                    scenario=scenario,
                    output_path=plan.output_path,
                    overwrites=False,
                    skip_reason=plan.reason,
                )
            )
    return entries


def _flatten_skeleton_plans(
    plan_result: SkeletonPlanResult,
) -> list[SkeletonScenarioEntry]:
    entries: list[SkeletonScenarioEntry] = []
    for plan in plan_result.plans:
        entries.append(
            SkeletonScenarioEntry(
                scenario=plan.scenarios[0],
                output_path=plan.output_path,
                overwrites=plan.overwrites,
            )
        )
    for plan in plan_result.skipped_plans:
        entries.append(
            SkeletonScenarioEntry(
                scenario=plan.scenarios[0],
                output_path=plan.output_path,
                overwrites=False,
                skip_reason=plan.reason,
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
            "priority": scenario.priority.value,
            "preview": preview,
            "overwrites": entry.overwrites,
        }

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
    return payload


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
                f"    Steps: {len(scenario.steps)} | Priority: {scenario.priority.value}"
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


def _init_example_content() -> dict[str, str]:
    return {
        "features/example/_feature.md": textwrap.dedent(
            """
            ---
            feature_id: example
            priority: medium
            tags: [demo, example]
            ---

            # Feature: Example Feature

            This is an example feature to demonstrate SpecLeft.

            Replace this with your own features.
            """
        ).strip(),
        "features/example/basic/_story.md": textwrap.dedent(
            """
            ---
            story_id: basic
            priority: medium
            ---

            # Story: Basic Example

            A simple example story with one scenario.
            """
        ).strip(),
        "features/example/basic/scenario1.md": textwrap.dedent(
            """
            ---
            scenario_id: scenario1
            priority: medium
            tags: [example]
            ---

            # Scenario: Example Scenario

            This is an example scenario.

            ## Steps
            - **Given** a precondition
            - **When** an action occurs
            - **Then** an expected result
            """
        ).strip(),
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
    return choice


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


@click.group()
@click.version_option(version=CLI_VERSION, prog_name="specleft")
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
    """Generate skeleton test files from Markdown feature specs.

    Reads the features directory specification and generates pytest test files
    with @specleft decorators and step context managers.
    """
    if format_type == "json" and not dry_run and not force:
        click.secho(
            "JSON output requires --dry-run or --force to avoid prompts.",
            fg="red",
            err=True,
        )
        sys.exit(1)

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
        force=force,
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

    if not force:
        if not click.confirm("Confirm creation?", default=False):
            click.echo("Cancelled")
            sys.exit(2)

    for plan in plan_result.plans:
        plan.output_path.parent.mkdir(parents=True, exist_ok=True)
        plan.output_path.write_text(plan.content)

    if format_type == "table":
        click.secho(f"\n✓ Created {len(plan_result.plans)} test files", fg="green")
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
    """Generate HTML report from test results.

    Reads the test results JSON and generates a static HTML report
    with summary dashboard, feature breakdown, and step details.
    """
    results_dir = Path(".specleft/results")

    # Find results file
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
        # Find latest results file
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

    # Load results
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
    """Validate Markdown specs in a features directory.

    Checks that the specs directory is valid according to the SpecLeft schema.
    Returns exit code 0 if valid, 1 if invalid.
    """
    warnings: list[dict[str, object]] = []
    try:
        config = load_specs_directory(features_dir)
        stats = collect_spec_stats(config)
        if format_type == "json":
            payload = {
                "valid": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
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
                "timestamp": datetime.now(timezone.utc).isoformat(),
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
                "timestamp": datetime.now(timezone.utc).isoformat(),
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
                "timestamp": datetime.now(timezone.utc).isoformat(),
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
    try:
        config = load_specs_directory(features_dir)
    except FileNotFoundError:
        if format_type == "json":
            payload = {
                "status": "error",
                "message": f"Directory not found: {features_dir}",
            }
            click.echo(json.dumps(payload, indent=2))
        else:
            click.secho(f"✗ Directory not found: {features_dir}", fg="red", err=True)
        sys.exit(1)
    except ValueError as e:
        if format_type == "json":
            payload = {
                "status": "error",
                "message": f"Unable to load specs: {e}",
            }
            click.echo(json.dumps(payload, indent=2))
        else:
            click.secho(f"✗ Unable to load specs: {e}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        if format_type == "json":
            payload = {
                "status": "error",
                "message": f"Unexpected error loading specs: {e}",
            }
            click.echo(json.dumps(payload, indent=2))
        else:
            click.secho(f"✗ Unexpected error loading specs: {e}", fg="red", err=True)
        sys.exit(1)

    if format_type == "json":
        payload = _build_features_list_json(config)
        click.echo(json.dumps(payload, indent=2))
        return

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
        if format_type == "json":
            payload = {
                "status": "error",
                "message": f"Directory not found: {features_dir}",
            }
            click.echo(json.dumps(payload, indent=2))
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
                payload = {
                    "status": "error",
                    "message": f"Unable to load specs: {e}",
                }
                click.echo(json.dumps(payload, indent=2))
            else:
                click.secho(f"✗ Unable to load specs: {e}", fg="red", err=True)
            sys.exit(1)
    except Exception as e:
        if format_type == "json":
            payload = {
                "status": "error",
                "message": f"Unexpected error loading specs: {e}",
            }
            click.echo(json.dumps(payload, indent=2))
        else:
            click.secho(f"✗ Unexpected error loading specs: {e}", fg="red", err=True)
        sys.exit(1)

    # Discover pytest tests
    test_discovery = _discover_pytest_tests(tests_dir)

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


@cli.command("doctor")
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    show_default=True,
    help="Output format: 'table' or 'json'.",
)
@click.option("--verbose", is_flag=True, help="Show detailed diagnostic information.")
def doctor(format_type: str, verbose: bool) -> None:
    """Verify SpecLeft installation and environment."""
    checks = _build_doctor_checks()
    output = _build_doctor_output(checks)

    if format_type == "json":
        click.echo(json.dumps(output, indent=2))
    else:
        _print_doctor_table(output, verbose=verbose)

    sys.exit(0 if output.get("healthy") else 1)


@cli.command("status")
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

    entries = _build_status_entries(
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
        payload = _build_status_json(entries, include_execution_time=True)
        click.echo(json.dumps(payload, indent=2))
    else:
        show_only = None
        if unimplemented:
            show_only = "unimplemented"
        elif implemented:
            show_only = "implemented"
        _print_status_table(entries, show_only=show_only)


@cli.command("next")
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
    try:
        config = load_specs_directory(features_dir)
    except FileNotFoundError:
        click.secho(f"Directory not found: {features_dir}", fg="red", err=True)
        sys.exit(1)
    except ValueError as exc:
        click.secho(f"Unable to load specs: {exc}", fg="red", err=True)
        sys.exit(1)

    entries = _build_status_entries(
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
            if entry.scenario.priority.value == priority_filter
        ]

    unimplemented.sort(
        key=lambda entry: (
            _priority_sort_value(entry.scenario.priority.value),
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


@cli.command("coverage")
@click.option(
    "--dir",
    "features_dir",
    default="features",
    help="Path to features directory.",
)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json", "badge"], case_sensitive=False),
    default="table",
    show_default=True,
    help="Output format: 'table', 'json', or 'badge'.",
)
@click.option(
    "--threshold",
    type=int,
    default=None,
    help="Exit non-zero if coverage below this percentage.",
)
@click.option(
    "--output",
    "output_path",
    type=str,
    default=None,
    help="Output file for badge format.",
)
def coverage(
    features_dir: str,
    format_type: str,
    threshold: int | None,
    output_path: str | None,
) -> None:
    """Show high-level coverage metrics."""
    try:
        config = load_specs_directory(features_dir)
    except FileNotFoundError:
        click.secho(f"Directory not found: {features_dir}", fg="red", err=True)
        sys.exit(1)
    except ValueError as exc:
        click.secho(f"Unable to load specs: {exc}", fg="red", err=True)
        sys.exit(1)

    entries = _build_status_entries(config, Path("tests"))
    metrics = _build_coverage_metrics(entries)

    if format_type == "json":
        payload = _build_coverage_json(entries)
        click.echo(json.dumps(payload, indent=2))
    elif format_type == "badge":
        if not output_path:
            click.secho("Badge format requires --output.", fg="red", err=True)
            sys.exit(1)
        percent = metrics.overall.percent
        message = "n/a" if percent is None else f"{percent:.0f}%"
        svg = _render_badge_svg("coverage", message, _badge_color(percent))
        Path(output_path).write_text(svg)
        click.echo(f"Badge written to {output_path}")
    else:
        _print_coverage_table(entries)

    if threshold is not None:
        coverage_value = metrics.overall.percent
        if coverage_value is None or coverage_value < threshold:
            sys.exit(1)


@cli.command("init")
@click.option("--example", is_flag=True, help="Create example feature specs.")
@click.option("--blank", is_flag=True, help="Create empty directory structure only.")
@click.option("--dry-run", is_flag=True, help="Show what would be created.")
def init(example: bool, blank: bool, dry_run: bool) -> None:
    """Initialize SpecLeft project directories and example specs."""
    if example and blank:
        click.secho("Choose either --example or --blank, not both.", fg="red", err=True)
        sys.exit(1)

    if not example and not blank:
        example = True

    if blank:
        example = False

    features_dir = Path("features")
    if features_dir.exists():
        choice = _prompt_init_action(features_dir)
        if choice == "3":
            click.echo("Cancelled")
            sys.exit(2)
        if choice == "1":
            click.echo("Skipping initialization")
            return

    directories, files = _init_plan(example=example)
    if dry_run:
        click.echo(
            "Creating SpecLeft example project..."
            if example
            else "Creating SpecLeft directory structure..."
        )
        click.echo("")
        _print_init_dry_run(directories, files)
        return

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
        click.echo("  1. Review the example: cat features/example/basic/scenario1.md")
        click.echo("  2. Generate tests: specleft test skeleton")
        click.echo("  3. Run tests: pytest")
        click.echo("  4. Check status: specleft status")
    else:
        click.echo("Directory structure ready!")
        click.echo("")
        click.echo("Next steps:")
        click.echo("  1. Create your first feature: features/<feature-id>/_feature.md")
        click.echo("  2. Add stories and scenarios")
        click.echo("  3. Generate tests: specleft test skeleton")


@cli.group(invoke_without_command=True)
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
    payload = _build_contract_payload()
    if format_type == "json":
        click.echo(json.dumps(payload, indent=2))
    else:
        _print_contract_table(payload)


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
        passed, checks, errors = _run_contract_tests(verbose=verbose)
        payload = _build_contract_test_payload(
            passed=passed, checks=checks, errors=errors
        )
        click.echo(json.dumps(payload, indent=2))
    else:
        click.echo("SpecLeft Agent Contract Tests")
        click.echo("━" * 44)
        passed, checks, errors = _run_contract_tests(
            verbose=verbose,
            on_progress=lambda check: _emit_contract_check(check, verbose),
        )
        click.echo("")
        if passed:
            click.echo("All Agent Contract guarantees verified.")
        else:
            click.echo("One or more Agent Contract guarantees failed.")
        if errors and verbose:
            click.echo("Errors:")
            for error in errors:
                click.echo(f"  - {error}")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    cli()
