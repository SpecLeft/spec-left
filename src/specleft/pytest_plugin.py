"""Pytest plugin for SpecLeft test collection and result capture.

This plugin provides:
- Automatic collection of @specleft decorated tests
- Auto-skip for tests whose scenarios are removed from specs
- Runtime marker injection from scenario tags
- Step-by-step result capture
- Result persistence to .specleft/results/
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from specleft.decorators import get_current_steps

if TYPE_CHECKING:
    from pytest import Config, Item, Session

logger = logging.getLogger(__name__)


def pytest_configure(config: Config) -> None:
    """Register the SpecLeft plugin and initialize result collection.

    Called after command line options are parsed and all plugins are loaded.
    """
    config._specleft_results = []  # type: ignore[attr-defined]
    config._specleft_start_time = datetime.now()  # type: ignore[attr-defined]
    config._specleft_specs_config = None  # type: ignore[attr-defined]

    # Register custom markers
    config.addinivalue_line("markers", "specleft: mark test as a SpecLeft managed test")


def _load_specs_config(
    config: Config,
) -> dict[tuple[str, str], dict[str, Any]] | None:
    """Load Markdown specs and build a lookup of valid scenarios.

    Args:
        config: Pytest config object.

    Returns:
        Dictionary mapping (feature_id, scenario_id) to scenario info,
        or None if specs are not found or invalid.
    """
    try:
        from specleft.validator import load_specs_directory
    except ImportError:
        logger.warning("Spec parser not available; skipping specs validation.")
        return None

    # Try multiple potential locations for specs
    search_paths = [
        Path("features"),
        Path("examples/features"),
        config.rootpath / "features",
        config.rootpath / "examples" / "features",
    ]

    specs_dir = None
    for path in search_paths:
        if path.exists():
            specs_dir = path
            break

    if specs_dir is None:
        logger.warning(
            "Specs directory not found. Running all @specleft tests without validation. "
            "Create a features directory to enable scenario validation and marker injection."
        )
        return None

    try:
        specs_config = load_specs_directory(specs_dir)
        config._specleft_specs_config = specs_config  # type: ignore[attr-defined]

        # Build lookup of valid (feature_id, scenario_id) pairs and their info
        valid_scenarios: dict[tuple[str, str], dict[str, Any]] = {}
        for feature in specs_config.features:
            for story in feature.stories:
                for scenario in story.scenarios:
                    key = (feature.feature_id, scenario.scenario_id)
                    valid_scenarios[key] = {
                        "tags": scenario.tags,
                        "feature_name": feature.name,
                        "scenario_name": scenario.name,
                        "priority": scenario.priority.value,
                    }
        return valid_scenarios
    except FileNotFoundError:
        logger.warning(
            "Specs directory not found. Running all @specleft tests without validation."
        )
        return None
    except ValueError as e:
        logger.error(f"Error loading specs: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading specs: {e}")
        return None


def _sanitize_marker_name(tag: str) -> str:
    """Sanitize a tag name to be a valid pytest marker.

    Args:
        tag: The tag name to sanitize.

    Returns:
        A valid pytest marker name.
    """
    # Replace hyphens and spaces with underscores
    return tag.replace("-", "_").replace(" ", "_")


def pytest_collection_modifyitems(
    session: Session, config: Config, items: list[Item]
) -> None:
    """Hook called after test collection to extract SpecLeft metadata.

    Identifies tests decorated with @specleft and extracts their metadata
    for later result collection. Also handles:
    - Auto-skip for tests whose scenarios are removed from specs
    - Runtime marker injection from scenario tags
    """
    # Load specs once for validation and marker injection
    valid_scenarios = _load_specs_config(config)

    for item in items:
        # Get the original function (unwrap any wrappers)
        func = getattr(item, "function", None)
        if func is None:
            continue

        # Check if this test has SpecLeft metadata
        feature_id = getattr(func, "_specleft_feature_id", None)
        scenario_id = getattr(func, "_specleft_scenario_id", None)

        if feature_id is not None and scenario_id is not None:
            # Extract metadata
            metadata: dict[str, Any] = {
                "feature_id": feature_id,
                "scenario_id": scenario_id,
                "test_name": item.name,
                "original_name": (
                    item.originalname if hasattr(item, "originalname") else item.name
                ),
                "nodeid": item.nodeid,
            }

            # Extract parameters if parameterized
            if hasattr(item, "callspec"):
                metadata["parameters"] = dict(item.callspec.params)
                metadata["is_parameterized"] = True
            else:
                metadata["parameters"] = {}
                metadata["is_parameterized"] = False

            # Store metadata on the item for later access
            item._specleft_metadata = metadata  # type: ignore[attr-defined]

            # Add the specleft marker
            item.add_marker(pytest.mark.specleft)

            # Auto-skip and marker injection (only if specs were loaded)
            if valid_scenarios is not None:
                scenario_key = (feature_id, scenario_id)

                if scenario_key not in valid_scenarios:
                    # Auto-skip: Scenario not found in specs
                    skip_marker = pytest.mark.skip(
                        reason=(
                            f"Scenario '{scenario_id}' (feature: {feature_id}) not found "
                            f"in specs. This test is orphaned and should be removed "
                            f"or the scenario should be re-added."
                        )
                    )
                    item.add_marker(skip_marker)
                    logger.warning(f"Skipping {item.nodeid}: scenario not in specs")
                else:
                    # Runtime marker injection from tags
                    scenario_info = valid_scenarios[scenario_key]
                    for tag in scenario_info["tags"]:
                        marker_name = _sanitize_marker_name(tag)
                        marker = getattr(pytest.mark, marker_name)
                        item.add_marker(marker)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: Item, call: Any) -> Any:
    """Capture test results and steps after test execution.

    This is a hookwrapper that intercepts test reports to collect
    SpecLeft-specific data including step results.
    """
    outcome = yield
    report = outcome.get_result()

    # Only collect results from the test call phase (not setup/teardown)
    if report.when != "call":
        return

    # Check if this is a SpecLeft test
    metadata = getattr(item, "_specleft_metadata", None)
    if metadata is None:
        return

    # Get steps from thread-local storage
    steps = get_current_steps()

    # Build the result record
    result: dict[str, Any] = {
        **metadata,
        "status": report.outcome,  # "passed", "failed", "skipped"
        "duration": report.duration,
        "error": str(report.longrepr) if report.failed else None,
        "steps": [
            {
                "description": step.description,
                "status": step.status,
                "duration": (
                    (step.end_time - step.start_time).total_seconds()
                    if step.end_time
                    else 0
                ),
                "error": step.error,
            }
            for step in steps
        ],
    }

    # Store result in config for later collection
    item.config._specleft_results.append(result)  # type: ignore[attr-defined]


def pytest_sessionfinish(session: Session, exitstatus: int) -> None:
    """Save results to disk after test session completes.

    Called after all tests have run and before pytest exits.
    """
    results = getattr(session.config, "_specleft_results", [])

    # Only process if there are SpecLeft results
    if not results:
        return

    # Import here to avoid circular imports
    from specleft.collector import ResultCollector

    collector = ResultCollector()
    results_data = collector.collect(results)
    filepath = collector.write(results_data)

    # Print summary to console
    summary = results_data["summary"]
    print(f"\n{'=' * 60}")
    print("SpecLeft Test Results")
    print(f"{'=' * 60}")
    print(f"Total Executions: {summary['total_executions']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Skipped: {summary['skipped']}")
    print(f"Duration: {summary['duration']:.2f}s")
    print(f"\nResults saved to: {filepath}")
    print(f"{'=' * 60}\n")
