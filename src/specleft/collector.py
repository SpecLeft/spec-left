"""Result collector for SpecLeft test results."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


class ResultCollector:
    """Collects and stores test results in JSON format."""

    def __init__(self, output_dir: str = ".specleft/results") -> None:
        """Initialize the collector.

        Args:
            output_dir: Directory to store result files.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def collect(self, pytest_results: list[dict[str, Any]]) -> dict[str, Any]:
        """Transform pytest results into SpecLeft format.

        Args:
            pytest_results: List of raw pytest result dictionaries.

        Returns:
            Structured results grouped by feature and scenario.
        """
        # Group by feature, then scenario
        features_map: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for result in pytest_results:
            feature_id = result["feature_id"]
            scenario_id = result["scenario_id"]
            features_map[feature_id][scenario_id].append(result)

        # Build structured output
        features_list: list[dict[str, Any]] = []
        total_executions = 0
        total_passed = 0
        total_failed = 0
        total_skipped = 0
        total_duration = 0.0

        for feature_id, scenarios_data in features_map.items():
            scenarios_list: list[dict[str, Any]] = []

            for scenario_id, executions in scenarios_data.items():
                # Calculate scenario summary
                scenario_passed = sum(1 for e in executions if e["status"] == "passed")
                scenario_failed = sum(1 for e in executions if e["status"] == "failed")
                scenario_skipped = sum(
                    1 for e in executions if e["status"] == "skipped"
                )

                scenarios_list.append(
                    {
                        "scenario_id": scenario_id,
                        "scenario_name": executions[0].get(
                            "original_name", scenario_id
                        ),
                        "is_parameterized": executions[0].get(
                            "is_parameterized", False
                        ),
                        "executions": executions,
                        "summary": {
                            "total": len(executions),
                            "passed": scenario_passed,
                            "failed": scenario_failed,
                            "skipped": scenario_skipped,
                        },
                    }
                )

                total_executions += len(executions)
                total_passed += scenario_passed
                total_failed += scenario_failed
                total_skipped += scenario_skipped
                total_duration += sum(e.get("duration", 0) for e in executions)

            features_list.append(
                {
                    "feature_id": feature_id,
                    "feature_name": feature_id,  # TODO: Get from specs
                    "scenarios": scenarios_list,
                }
            )

        return {
            "run_id": datetime.now().isoformat(),
            "summary": {
                "total_features": len(features_list),
                "total_scenarios": sum(len(f["scenarios"]) for f in features_list),
                "total_executions": total_executions,
                "passed": total_passed,
                "failed": total_failed,
                "skipped": total_skipped,
                "duration": total_duration,
            },
            "features": features_list,
        }

    def write(self, data: dict[str, Any], filename: str | None = None) -> Path:
        """Write results to JSON file.

        Args:
            data: Structured results data.
            filename: Optional filename. If not provided, generates timestamped name.

        Returns:
            Path to the written file.
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"results_{timestamp}.json"

        filepath = self.output_dir / filename
        with filepath.open("w") as f:
            json.dump(data, f, indent=2, default=str)

        return filepath
