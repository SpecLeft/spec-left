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

    def test_nested_directory_creation(self) -> None:
        """Test that deeply nested directories are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            deep_dir = Path(tmpdir) / "a/b/c/d/e"
            collector = ResultCollector(output_dir=str(deep_dir))

            assert collector.output_dir.exists()

    def test_existing_directory_is_reused(self) -> None:
        """Test that existing directory is reused without error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "existing"
            output_dir.mkdir(parents=True)

            # Create a marker file
            marker = output_dir / "marker.txt"
            marker.write_text("exists")

            collector = ResultCollector(output_dir=str(output_dir))

            # Directory should still exist with marker
            assert collector.output_dir.exists()
            assert marker.exists()


class TestResultCollectorCollect:
    """Tests for ResultCollector.collect() method."""

    def test_empty_results(self) -> None:
        """Test collecting empty results list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)
            result = collector.collect([])

            assert "run_id" in result
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
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)

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
            assert len(feature["scenarios"]) == 1

            scenario = feature["scenarios"][0]
            assert scenario["scenario_id"] == "login-success"
            assert scenario["scenario_name"] == "Login Success"
            assert scenario["is_parameterized"] is False
            assert len(scenario["executions"]) == 1
            assert scenario["summary"]["total"] == 1
            assert scenario["summary"]["passed"] == 1

    def test_single_feature_multiple_scenarios(self) -> None:
        """Test collecting single feature with multiple scenarios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)

            pytest_results = [
                {
                    "feature_id": "AUTH-001",
                    "scenario_id": "login-success",
                    "test_name": "test_login_success",
                    "original_name": "Login Success",
                    "status": "passed",
                    "duration": 0.3,
                    "is_parameterized": False,
                    "steps": [],
                },
                {
                    "feature_id": "AUTH-001",
                    "scenario_id": "login-failure",
                    "test_name": "test_login_failure",
                    "original_name": "Login Failure",
                    "status": "passed",
                    "duration": 0.2,
                    "is_parameterized": False,
                    "steps": [],
                },
            ]

            result = collector.collect(pytest_results)

            assert result["summary"]["total_features"] == 1
            assert result["summary"]["total_scenarios"] == 2
            assert result["summary"]["total_executions"] == 2
            assert result["summary"]["passed"] == 2
            assert result["summary"]["duration"] == 0.5

            feature = result["features"][0]
            assert len(feature["scenarios"]) == 2

    def test_multiple_features(self) -> None:
        """Test collecting multiple features."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)

            pytest_results = [
                {
                    "feature_id": "AUTH-001",
                    "scenario_id": "login",
                    "test_name": "test_login",
                    "original_name": "Login",
                    "status": "passed",
                    "duration": 0.3,
                    "is_parameterized": False,
                    "steps": [],
                },
                {
                    "feature_id": "USER-001",
                    "scenario_id": "profile",
                    "test_name": "test_profile",
                    "original_name": "Profile",
                    "status": "passed",
                    "duration": 0.2,
                    "is_parameterized": False,
                    "steps": [],
                },
                {
                    "feature_id": "CART-001",
                    "scenario_id": "checkout",
                    "test_name": "test_checkout",
                    "original_name": "Checkout",
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

            feature_ids = [f["feature_id"] for f in result["features"]]
            assert "AUTH-001" in feature_ids
            assert "USER-001" in feature_ids
            assert "CART-001" in feature_ids

    def test_parameterized_tests(self) -> None:
        """Test collecting parameterized tests (multiple executions per scenario)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)

            pytest_results = [
                {
                    "feature_id": "CALC-001",
                    "scenario_id": "addition",
                    "test_name": "test_addition[1+2]",
                    "original_name": "Addition",
                    "status": "passed",
                    "duration": 0.1,
                    "is_parameterized": True,
                    "steps": [],
                },
                {
                    "feature_id": "CALC-001",
                    "scenario_id": "addition",
                    "test_name": "test_addition[3+4]",
                    "original_name": "Addition",
                    "status": "passed",
                    "duration": 0.1,
                    "is_parameterized": True,
                    "steps": [],
                },
                {
                    "feature_id": "CALC-001",
                    "scenario_id": "addition",
                    "test_name": "test_addition[5+6]",
                    "original_name": "Addition",
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

    def test_mixed_statuses(self) -> None:
        """Test collecting results with mixed statuses."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)

            pytest_results = [
                {
                    "feature_id": "TEST-001",
                    "scenario_id": "pass",
                    "test_name": "test_pass",
                    "status": "passed",
                    "duration": 0.1,
                    "is_parameterized": False,
                    "steps": [],
                },
                {
                    "feature_id": "TEST-001",
                    "scenario_id": "fail",
                    "test_name": "test_fail",
                    "status": "failed",
                    "duration": 0.2,
                    "is_parameterized": False,
                    "steps": [],
                },
                {
                    "feature_id": "TEST-001",
                    "scenario_id": "skip",
                    "test_name": "test_skip",
                    "status": "skipped",
                    "duration": 0.0,
                    "is_parameterized": False,
                    "steps": [],
                },
            ]

            result = collector.collect(pytest_results)

            assert result["summary"]["passed"] == 1
            assert result["summary"]["failed"] == 1
            assert result["summary"]["skipped"] == 1
            assert result["summary"]["total_executions"] == 3

    def test_run_id_is_iso_format(self) -> None:
        """Test that run_id is in ISO datetime format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)
            result = collector.collect([])

            # Should be parseable as ISO datetime
            run_id = result["run_id"]
            try:
                datetime.fromisoformat(run_id)
            except ValueError:
                pytest.fail(f"run_id '{run_id}' is not valid ISO format")

    def test_duration_calculation(self) -> None:
        """Test that total duration is calculated correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)

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

    def test_missing_duration_defaults_to_zero(self) -> None:
        """Test that missing duration defaults to zero."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)

            pytest_results = [
                {
                    "feature_id": "TEST-001",
                    "scenario_id": "a",
                    "test_name": "test_a",
                    "status": "passed",
                    # No duration field
                    "is_parameterized": False,
                    "steps": [],
                },
            ]

            result = collector.collect(pytest_results)

            assert result["summary"]["duration"] == 0.0

    def test_original_name_fallback(self) -> None:
        """Test that scenario_id is used when original_name is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)

            pytest_results = [
                {
                    "feature_id": "TEST-001",
                    "scenario_id": "my-scenario",
                    "test_name": "test_my_scenario",
                    "status": "passed",
                    "duration": 0.1,
                    "is_parameterized": False,
                    "steps": [],
                    # No original_name field
                },
            ]

            result = collector.collect(pytest_results)

            scenario = result["features"][0]["scenarios"][0]
            assert scenario["scenario_name"] == "my-scenario"

    def test_steps_are_preserved(self) -> None:
        """Test that step data is preserved in results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)

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
                },
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

            # Read and parse JSON
            with filepath.open() as f:
                loaded = json.load(f)

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

            # Should not raise and file should exist
            assert filepath.exists()

            # Read and verify datetime was serialized as string
            with filepath.open() as f:
                loaded = json.load(f)

            assert loaded["timestamp"] == str(now)
            assert loaded["nested"]["time"] == str(now)

    def test_write_indented_json(self) -> None:
        """Test that written JSON is properly indented."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)
            data = {"key1": "value1", "key2": {"nested": "value"}}

            filepath = collector.write(data)

            content = filepath.read_text()
            # Should have newlines (indented)
            assert "\n" in content
            # Should have indentation (spaces)
            assert "  " in content

    def test_write_returns_correct_path(self) -> None:
        """Test that write returns the correct file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "results"
            collector = ResultCollector(output_dir=str(output_dir))

            filepath = collector.write({"data": True}, filename="test.json")

            expected = output_dir / "test.json"
            assert filepath == expected

    def test_write_overwrites_existing_file(self) -> None:
        """Test that write overwrites existing file with same name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)

            # Write first time
            collector.write({"version": 1}, filename="results.json")

            # Write second time with different data
            filepath = collector.write({"version": 2}, filename="results.json")

            with filepath.open() as f:
                loaded = json.load(f)

            assert loaded["version"] == 2


class TestResultCollectorIntegration:
    """Integration tests for ResultCollector."""

    def test_collect_and_write_full_workflow(self) -> None:
        """Test full workflow: collect results and write to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)

            pytest_results = [
                {
                    "feature_id": "AUTH-001",
                    "scenario_id": "login",
                    "test_name": "test_login",
                    "original_name": "User Login",
                    "status": "passed",
                    "duration": 0.5,
                    "is_parameterized": False,
                    "steps": [
                        {"description": "Given user on login page", "status": "passed"},
                        {"description": "When enters credentials", "status": "passed"},
                        {"description": "Then sees dashboard", "status": "passed"},
                    ],
                },
                {
                    "feature_id": "AUTH-001",
                    "scenario_id": "logout",
                    "test_name": "test_logout",
                    "original_name": "User Logout",
                    "status": "passed",
                    "duration": 0.3,
                    "is_parameterized": False,
                    "steps": [],
                },
            ]

            # Collect results
            collected = collector.collect(pytest_results)

            # Write to file
            filepath = collector.write(collected, filename="test_results.json")

            # Verify file contents
            with filepath.open() as f:
                loaded = json.load(f)

            assert loaded["summary"]["total_features"] == 1
            assert loaded["summary"]["total_scenarios"] == 2
            assert loaded["summary"]["passed"] == 2
            assert loaded["summary"]["duration"] == 0.8

            feature = loaded["features"][0]
            assert feature["feature_id"] == "AUTH-001"
            assert len(feature["scenarios"]) == 2

            login_scenario = next(
                s for s in feature["scenarios"] if s["scenario_id"] == "login"
            )
            assert login_scenario["scenario_name"] == "User Login"
            assert len(login_scenario["executions"][0]["steps"]) == 3

    def test_multiple_collect_calls_are_independent(self) -> None:
        """Test that multiple collect calls don't affect each other."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ResultCollector(output_dir=tmpdir)

            results1 = [
                {
                    "feature_id": "A",
                    "scenario_id": "a",
                    "test_name": "test_a",
                    "status": "passed",
                    "duration": 1.0,
                    "is_parameterized": False,
                    "steps": [],
                },
            ]

            results2 = [
                {
                    "feature_id": "B",
                    "scenario_id": "b",
                    "test_name": "test_b",
                    "status": "failed",
                    "duration": 2.0,
                    "is_parameterized": False,
                    "steps": [],
                },
            ]

            collected1 = collector.collect(results1)
            collected2 = collector.collect(results2)

            # Each should be independent
            assert collected1["summary"]["total_features"] == 1
            assert collected1["features"][0]["feature_id"] == "A"
            assert collected1["summary"]["passed"] == 1

            assert collected2["summary"]["total_features"] == 1
            assert collected2["features"][0]["feature_id"] == "B"
            assert collected2["summary"]["failed"] == 1
