"""SpecLeft Pytest Plugin."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, TypedDict, cast

import pytest

from specleft.decorators import get_current_steps
from specleft.schema import FeatureSpec, ScenarioSpec, SpecsConfig


class SpecleftMetadata(TypedDict, total=False):
    feature_id: str
    scenario_id: str
    test_name: str
    original_name: str
    nodeid: str
    is_parameterized: bool
    parameters: dict[str, Any]
    feature_name: str | None
    scenario_name: str | None
    tags: list[str]


class _SpecleftConfig(Protocol):
    _specleft_results: list[dict[str, Any]]
    _specleft_start_time: datetime
    _specleft_specs_config: SpecsConfig | None


class _SpecleftItem(Protocol):
    _specleft_metadata: SpecleftMetadata
    config: pytest.Config


def _as_specleft_config(config: pytest.Config) -> _SpecleftConfig:
    return cast(_SpecleftConfig, config)


def _as_specleft_item(item: pytest.Item) -> _SpecleftItem:
    return cast(_SpecleftItem, item)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addini(
        "specleft_features_dir",
        "Directory containing SpecLeft specs",
        default="features",
    )
    parser.addini(
        "specleft_output_dir",
        "Output directory for SpecLeft results",
        default=".specleft",
    )
    parser.addini(
        "specleft_tag",
        "Default SpecLeft tag filters",
        default=[],
        type="args",
    )
    parser.addini(
        "specleft_priority",
        "Default SpecLeft priority filters",
        default=[],
        type="args",
    )
    parser.addini(
        "specleft_feature",
        "Default SpecLeft feature filters",
        default=[],
        type="args",
    )
    parser.addini(
        "specleft_scenario",
        "Default SpecLeft scenario filters",
        default=[],
        type="args",
    )
    parser.addoption(
        "--specleft-tag",
        action="append",
        default=[],
        dest="specleft_tags",
        help="Filter SpecLeft tests by scenario tag (repeatable)",
    )
    parser.addoption(
        "--specleft-priority",
        action="append",
        default=[],
        dest="specleft_priorities",
        help="Filter SpecLeft tests by scenario priority (repeatable)",
    )
    parser.addoption(
        "--specleft-feature",
        action="append",
        default=[],
        dest="specleft_features",
        help="Filter SpecLeft tests by feature_id (repeatable)",
    )
    parser.addoption(
        "--specleft-scenario",
        action="append",
        default=[],
        dest="specleft_scenarios",
        help="Filter SpecLeft tests by scenario_id (repeatable)",
    )


def pytest_configure(config: pytest.Config) -> None:
    specleft_config = _as_specleft_config(config)
    specleft_config._specleft_results = []
    specleft_config._specleft_start_time = datetime.now()
    specleft_config._specleft_specs_config = None

    config.addinivalue_line(
        "markers",
        "specleft(feature_id, scenario_id): Mark test with SpecLeft metadata",
    )

    # Load specs and register dynamic markers from scenario tags
    specs_config = _load_specs_config(config)
    specleft_config._specleft_specs_config = specs_config

    if specs_config:
        # Register tag-based markers from scenarios
        for tag in _collect_all_tags(specs_config):
            marker_name = _sanitize_marker_name(tag)
            config.addinivalue_line(
                "markers",
                f"{marker_name}: SpecLeft scenario tag '{tag}'",
            )

        # Register priority markers
        from specleft.schema import Priority

        for priority in Priority:
            marker_name = f"priority_{priority.value}"
            config.addinivalue_line(
                "markers",
                f"{marker_name}: SpecLeft priority level '{priority.value}'",
            )


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(
    session: pytest.Session, config: pytest.Config, items: list[pytest.Item]
) -> None:
    specleft_config = _as_specleft_config(config)
    tag_filters = {
        tag.strip()
        for tag in (config.getini("specleft_tag") or [])
        + (config.getoption("specleft_tags") or [])
    }
    priority_filters = {
        priority.strip().lower()
        for priority in (config.getini("specleft_priority") or [])
        + (config.getoption("specleft_priorities") or [])
    }
    feature_filters = {
        feature.strip()
        for feature in (config.getini("specleft_feature") or [])
        + (config.getoption("specleft_features") or [])
    }
    scenario_filters = {
        scenario.strip()
        for scenario in (config.getini("specleft_scenario") or [])
        + (config.getoption("specleft_scenarios") or [])
    }
    use_filters = any(
        (tag_filters, priority_filters, feature_filters, scenario_filters)
    )

    specs_config = _load_specs_config(config)
    specleft_config._specleft_specs_config = specs_config

    if not specs_config and use_filters:
        for item in items:
            func = getattr(item, "function", None)
            if func is None:
                continue
            feature_id = getattr(func, "_specleft_feature_id", None)
            scenario_id = getattr(func, "_specleft_scenario_id", None)
            if feature_id is None or scenario_id is None:
                continue
            item.add_marker(
                pytest.mark.skip(
                    reason=(
                        "SpecLeft filters require specs. " "No specs directory found."
                    )
                )
            )
        return
    use_filters = any(
        (tag_filters, priority_filters, feature_filters, scenario_filters)
    )

    for item in items:
        func = getattr(item, "function", None)
        if func is None:
            continue

        feature_id = getattr(func, "_specleft_feature_id", None)
        scenario_id = getattr(func, "_specleft_scenario_id", None)

        if feature_id is None or scenario_id is None:
            continue

        specleft_item = _as_specleft_item(item)
        specleft_item._specleft_metadata = {
            "feature_id": feature_id,
            "scenario_id": scenario_id,
            "test_name": item.name,
            "original_name": getattr(item, "originalname", item.name),
            "nodeid": item.nodeid,
            "is_parameterized": hasattr(item, "callspec"),
            "parameters": (
                dict(item.callspec.params) if hasattr(item, "callspec") else {}
            ),
        }

        scenario = None
        feature = None
        if specs_config:
            scenario, feature = _find_scenario(specs_config, scenario_id)
            if scenario:
                for tag in scenario.tags:
                    marker_name = _sanitize_marker_name(tag)
                    item.add_marker(getattr(pytest.mark, marker_name))
                priority_marker = f"priority_{scenario.priority.value}"
                item.add_marker(getattr(pytest.mark, priority_marker))

        if use_filters and not _matches_filters(
            feature_id=feature_id,
            scenario_id=scenario_id,
            scenario=scenario,
            tag_filters=tag_filters,
            priority_filters=priority_filters,
            feature_filters=feature_filters,
            scenario_filters=scenario_filters,
        ):
            item.add_marker(pytest.mark.skip(reason="Filtered by SpecLeft selection"))

        if specs_config and scenario is None:
            item.add_marker(
                pytest.mark.skip(
                    reason=(
                        f"Scenario '{scenario_id}' (feature: {feature_id}) "
                        "not found in specs."
                    )
                )
            )
        else:
            specleft_item._specleft_metadata.update(
                {
                    "feature_name": feature.name if feature else None,
                    "scenario_name": scenario.name if scenario else None,
                    "tags": list(scenario.tags) if scenario else [],
                }
            )


def _sanitize_marker_name(tag: str) -> str:
    """Sanitize a tag name to be a valid pytest marker."""
    return tag.replace("-", "_")


def _collect_all_tags(specs_config: SpecsConfig) -> set[str]:
    """Collect all unique tags from all scenarios in specs."""
    tags: set[str] = set()
    for feature in specs_config.features:
        for story in feature.stories:
            for scenario in story.scenarios:
                tags.update(scenario.tags)
    return tags


def _load_specs_config(config: pytest.Config) -> SpecsConfig | None:
    features_dir = config.getini("specleft_features_dir") or "features"
    search_roots = [
        Path(str(config.rootpath)),
        Path.cwd(),
        Path(__file__).resolve().parent.parent.parent,
    ]

    for root in search_roots:
        root_path = Path(str(root))
        features_path = Path(features_dir)
        if not features_path.is_absolute():
            features_path = root_path / features_path

        if not features_path.exists():
            continue

        try:
            from specleft.validator import load_specs_directory

            return load_specs_directory(features_path)
        except Exception:
            try:
                from specleft.schema import SpecsConfig

                parsed = SpecsConfig.from_directory(features_path)
                return parsed if parsed.features else None
            except Exception:
                continue

    return None


def _find_scenario(
    specs_config: SpecsConfig, scenario_id: str
) -> tuple[ScenarioSpec | None, FeatureSpec | None]:
    for feature in specs_config.features:
        for story in feature.stories:
            for scenario in story.scenarios:
                if scenario.scenario_id == scenario_id:
                    return scenario, feature
    return None, None


def _matches_filters(
    feature_id: str,
    scenario_id: str,
    scenario: ScenarioSpec | None,
    tag_filters: set[str],
    priority_filters: set[str],
    feature_filters: set[str],
    scenario_filters: set[str],
) -> bool:
    if feature_filters and feature_id not in feature_filters:
        return False
    if scenario_filters and scenario_id not in scenario_filters:
        return False

    if scenario is None:
        return not tag_filters and not priority_filters

    scenario_tags = {_sanitize_marker_name(tag) for tag in scenario.tags}
    scenario_priority = scenario.priority.value.lower()

    if tag_filters and not scenario_tags.intersection(tag_filters):
        return False
    return not (priority_filters and scenario_priority not in priority_filters)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]) -> Any:
    outcome = yield
    report = outcome.get_result()

    metadata = cast(SpecleftMetadata | None, getattr(item, "_specleft_metadata", None))
    if metadata is None:
        return

    # Capture skipped tests during setup phase
    if report.when == "setup" and report.skipped:
        skip_reason = None
        if report.longrepr and isinstance(report.longrepr, tuple):
            skip_reason = str(report.longrepr[2]) if len(report.longrepr) > 2 else None
        elif report.longrepr:
            skip_reason = str(report.longrepr)

        result = {
            **metadata,
            "status": "skipped",
            "duration": report.duration,
            "error": None,
            "skip_reason": skip_reason,
            "steps": [],
        }
        specleft_config = _as_specleft_config(item.config)
        specleft_config._specleft_results.append(result)
        return

    # Capture passed/failed tests during call phase
    if report.when != "call":
        return

    steps = get_current_steps()

    result = {
        **metadata,
        "status": report.outcome,
        "duration": report.duration,
        "error": str(report.longrepr) if report.failed else None,
        "steps": [
            {
                "description": step.description,
                "status": step.status,
                "duration": step.duration,
                "error": step.error,
                "skipped_reason": step.skipped_reason,
            }
            for step in steps
        ],
    }
    specleft_config = _as_specleft_config(item.config)
    specleft_config._specleft_results.append(result)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    config = session.config
    specleft_config = _as_specleft_config(config)
    results = specleft_config._specleft_results

    if not results:
        return

    from specleft.collector import ResultCollector

    output_dir = config.getini("specleft_output_dir") or ".specleft"
    collector = ResultCollector(output_dir=f"{output_dir}/results")

    results_data = collector.collect(results)
    filepath = collector.write(results_data)

    summary = results_data["summary"]
    print(f"\n{'═' * 60}")
    print("SpecLeft Test Results")
    print(f"{'═' * 60}")
    print(f"Total Executions: {summary['total_executions']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Duration: {summary['duration']:.2f}s")
    print(f"\nResults saved to: {filepath}")
    print(f"{'═' * 60}\n")
