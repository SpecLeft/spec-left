"""Tests for specleft.collector module."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from specleft.collector import ResultCollector


class TestResultCollectorInit:
    """Tests for ResultCollector initialization."""

    def test_default_output_dir(self) -> None:
        """Test that default output directory is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / ".specleft/results"
            collector = ResultCollector(output_dir=str(output_dir))

            assert collector.output_dir.exists()
            assert collector.output_dir == output_dir

    def test_custom_output_dir(self) -> None:
        """Test that custom output directory is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_dir = Path(tmpdir) / "custom/results/dir"
            collector = ResultCollector(output_dir=str(custom_dir))

            assert collector.output_dir.exists()
            assert collector.output_dir == custom_dir


class TestResultCollectorCollect:
    """Tests for ResultCollector.collect() method."""

    def test_empty_results(self) -> None:
        """Test collecting empty results list."""
        collector = ResultCollector(output_dir=tempfile.mkdtemp())
        result = collector.collect([])

        assert result["summary"]["total_features"] == 0
        assert result["summary"]["total_scenarios"] == 0
        assert result["summary"]["total_executions"] == 0
        assert result["summary"]["passed"] == 0
        assert result["summary"]["failed"] == 0
        assert result["summary"]["skipped"] == 0
        assert result["summary"]["duration"] == 0.0
        assert result["features"] == []

    def test_single_feature_single_scenario(self) -> None:
        """Test collecting single feature with single scenario."""
        collector = ResultCollector(output_dir=tempfile.mkdtemp())

        pytest_results = [
            {
                "feature_id": "AUTH-001",
                "scenario_id": "login-success",
                "test_name": "test_login_success",
                "original_name": "Login Success",
                "status": "passed",
                "duration": 0.5,
                "is_parameterized": False,
                "steps": [],
            }
        ]

        result = collector.collect(pytest_results)

        assert result["summary"]["total_features"] == 1
        assert result["summary"]["total_scenarios"] == 1
        assert result["summary"]["total_executions"] == 1
        assert result["summary"]["passed"] == 1
        assert result["summary"]["failed"] == 0
        assert result["summary"]["duration"] == 0.5

        feature = result["features"][0]
        assert feature["feature_id"] == "AUTH-001"
        assert feature["feature_name"] is None
        assert len(feature["scenarios"]) == 1

        scenario = feature["scenarios"][0]
        assert scenario["scenario_id"] == "login-success"
        assert scenario["scenario_name"] is None
        assert scenario["is_parameterized"] is False
        assert len(scenario["executions"]) == 1
        assert scenario["summary"]["total"] == 1
        assert scenario["summary"]["passed"] == 1
        assert scenario["summary"]["failed"] == 0
        assert scenario["summary"]["skipped"] == 0

    def test_multiple_features(self) -> None:
        """Test collecting multiple features."""
        collector = ResultCollector(output_dir=tempfile.mkdtemp())

        pytest_results = [
            {
                "feature_id": "AUTH-001",
                "scenario_id": "login",
                "test_name": "test_login",
                "status": "passed",
                "duration": 0.3,
                "is_parameterized": False,
                "steps": [],
            },
            {
                "feature_id": "USER-001",
                "scenario_id": "profile",
                "test_name": "test_profile",
                "status": "passed",
                "duration": 0.2,
                "is_parameterized": False,
                "steps": [],
            },
            {
                "feature_id": "CART-001",
                "scenario_id": "checkout",
                "test_name": "test_checkout",
                "status": "failed",
                "duration": 0.4,
                "is_parameterized": False,
                "steps": [],
            },
        ]

        result = collector.collect(pytest_results)

        assert result["summary"]["total_features"] == 3
        assert result["summary"]["total_scenarios"] == 3
        assert result["summary"]["total_executions"] == 3
        assert result["summary"]["passed"] == 2
        assert result["summary"]["failed"] == 1
        assert result["summary"]["duration"] == 0.9

        feature_ids = {f["feature_id"] for f in result["features"]}
        assert feature_ids == {"AUTH-001", "USER-001", "CART-001"}

    def test_parameterized_tests(self) -> None:
        """Test collecting parameterized tests (multiple executions per scenario)."""
        collector = ResultCollector(output_dir=tempfile.mkdtemp())

        pytest_results = [
            {
                "feature_id": "CALC-001",
                "scenario_id": "addition",
                "test_name": "test_addition[1+2]",
                "status": "passed",
                "duration": 0.1,
                "is_parameterized": True,
                "steps": [],
            },
            {
                "feature_id": "CALC-001",
                "scenario_id": "addition",
                "test_name": "test_addition[3+4]",
                "status": "passed",
                "duration": 0.1,
                "is_parameterized": True,
                "steps": [],
            },
            {
                "feature_id": "CALC-001",
                "scenario_id": "addition",
                "test_name": "test_addition[5+6]",
                "status": "failed",
                "duration": 0.1,
                "is_parameterized": True,
                "steps": [],
            },
        ]

        result = collector.collect(pytest_results)

        assert result["summary"]["total_features"] == 1
        assert result["summary"]["total_scenarios"] == 1
        assert result["summary"]["total_executions"] == 3
        assert result["summary"]["passed"] == 2
        assert result["summary"]["failed"] == 1

        scenario = result["features"][0]["scenarios"][0]
        assert scenario["is_parameterized"] is True
        assert len(scenario["executions"]) == 3
        assert scenario["summary"]["total"] == 3
        assert scenario["summary"]["passed"] == 2
        assert scenario["summary"]["failed"] == 1
        assert scenario["summary"]["skipped"] == 0

    def test_skipped_results_counted(self) -> None:
        """Test collecting results with skipped status."""
        collector = ResultCollector(output_dir=tempfile.mkdtemp())

        pytest_results = [
            {
                "feature_id": "TEST-001",
                "scenario_id": "skip",
                "test_name": "test_skip",
                "status": "skipped",
                "duration": 0.0,
                "is_parameterized": False,
                "steps": [],
            }
        ]

        result = collector.collect(pytest_results)

        assert result["summary"]["skipped"] == 1
        assert result["summary"]["total_executions"] == 1

        scenario = result["features"][0]["scenarios"][0]
        assert scenario["summary"]["skipped"] == 1

    def test_run_id_is_iso_format(self) -> None:
        """Test that run_id is in ISO datetime format."""
        collector = ResultCollector(output_dir=tempfile.mkdtemp())
        result = collector.collect([])

        run_id = result["run_id"]
        try:
            datetime.fromisoformat(run_id)
        except ValueError:
            pytest.fail(f"run_id '{run_id}' is not valid ISO format")

    def test_duration_calculation(self) -> None:
        """Test that total duration is calculated correctly."""
        collector = ResultCollector(output_dir=tempfile.mkdtemp())

        pytest_results = [
            {
                "feature_id": "TEST-001",
                "scenario_id": "a",
                "test_name": "test_a",
                "status": "passed",
                "duration": 1.5,
                "is_parameterized": False,
                "steps": [],
            },
            {
                "feature_id": "TEST-001",
                "scenario_id": "b",
                "test_name": "test_b",
                "status": "passed",
                "duration": 2.5,
                "is_parameterized": False,
                "steps": [],
            },
            {
                "feature_id": "TEST-002",
                "scenario_id": "c",
                "test_name": "test_c",
                "status": "passed",
                "duration": 0.5,
                "is_parameterized": False,
                "steps": [],
            },
        ]

        result = collector.collect(pytest_results)

        assert result["summary"]["duration"] == 4.5

    def test_steps_are_preserved(self) -> None:
        """Test that step data is preserved in results."""
        collector = ResultCollector(output_dir=tempfile.mkdtemp())

        steps = [
            {
                "description": "Given user is logged in",
                "status": "passed",
                "duration": 0.1,
            },
            {
                "description": "When user clicks button",
                "status": "passed",
                "duration": 0.2,
            },
            {
                "description": "Then action is performed",
                "status": "failed",
                "duration": 0.1,
            },
        ]

        pytest_results = [
            {
                "feature_id": "TEST-001",
                "scenario_id": "with-steps",
                "test_name": "test_with_steps",
                "status": "failed",
                "duration": 0.4,
                "is_parameterized": False,
                "steps": steps,
            }
        ]

        result = collector.collect(pytest_results)

        execution = result["features"][0]["scenarios"][0]["executions"][0]
        assert execution["steps"] == steps


class TestResultCollectorWrite:
    """Tests for ResultCollector.write() method."""

    def test_write_with_auto_generated_filename(self) -> None:
        """Test write generates timestamped filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)
            data: dict[str, Any] = {"test": "data"}

            filepath = collector.write(data)

            assert filepath.exists()
            assert filepath.parent == collector.output_dir
            assert filepath.name.startswith("results_")
            assert filepath.name.endswith(".json")

    def test_write_with_custom_filename(self) -> None:
        """Test write with custom filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)
            data: dict[str, Any] = {"test": "data"}

            filepath = collector.write(data, filename="custom_results.json")

            assert filepath.exists()
            assert filepath.name == "custom_results.json"

    def test_write_creates_valid_json(self) -> None:
        """Test that written file contains valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)
            data = {
                "run_id": "2025-01-14T10:00:00",
                "summary": {"passed": 5, "failed": 2},
                "features": [{"id": "FEAT-001"}],
            }

            filepath = collector.write(data)

            with filepath.open() as file_obj:
                loaded = json.load(file_obj)

            assert loaded == data

    def test_write_with_datetime_objects(self) -> None:
        """Test that datetime objects are serialized correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)
            now = datetime.now()
            data: dict[str, Any] = {
                "timestamp": now,
                "nested": {"time": now},
            }

            filepath = collector.write(data)

            assert filepath.exists()

            with filepath.open() as file_obj:
                loaded = json.load(file_obj)

            assert loaded["timestamp"] == str(now)
            assert loaded["nested"]["time"] == str(now)

    def test_write_returns_correct_path(self) -> None:
        """Test that write returns the correct file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "results"
            collector = ResultCollector(output_dir=str(output_dir))

            filepath = collector.write({"data": True}, filename="test.json")

            expected = output_dir / "test.json"
            assert filepath == expected


class TestResultCollectorLatestResults:
    """Tests for ResultCollector.get_latest_results."""

    def test_get_latest_results_returns_none(self) -> None:
        """Test no results returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)
            assert collector.get_latest_results() is None

    def test_get_latest_results_returns_latest(self) -> None:
        """Test latest results file returned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)
            collector.write({"version": 1}, filename="results_20250101_000000.json")
            collector.write({"version": 2}, filename="results_20250101_000001.json")

            latest = collector.get_latest_results()

            assert latest == {"version": 2}
