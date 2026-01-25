"""Tests for specleft.decorators module."""

from __future__ import annotations

import concurrent.futures
import importlib
import threading
import time
from datetime import datetime

import pytest
import specleft.decorators as decorators
from specleft.decorators import (
    StepResult,
    _get_context,
    _reset_context,
    clear_steps,
    get_current_metadata,
    get_current_steps,
    is_in_specleft_test,
    shared_step,
    specleft,
    step,
)


class TestStepResult:
    """Tests for StepResult dataclass."""

    def test_minimal_step_result(self) -> None:
        """Test creating StepResult with required fields only."""
        now = datetime.now()
        result = StepResult(description="Test step", start_time=now)
        assert result.description == "Test step"
        assert result.status == "passed"
        assert result.start_time == now
        assert result.end_time is None
        assert result.error is None
        assert result.skipped_reason is None

    def test_full_step_result(self) -> None:
        """Test creating StepResult with all fields."""
        start = datetime.now()
        end = datetime.now()
        result = StepResult(
            description="Failed step",
            status="failed",
            start_time=start,
            end_time=end,
            error="Something went wrong",
            skipped_reason="Not needed",
        )
        assert result.description == "Failed step"
        assert result.status == "failed"
        assert result.end_time == end
        assert result.error == "Something went wrong"
        assert result.skipped_reason == "Not needed"

    def test_duration_returns_zero_without_end_time(self) -> None:
        """Test duration property when end_time is missing."""
        result = StepResult(description="Test", start_time=datetime.now())
        assert result.duration == 0.0

    def test_duration_returns_seconds(self) -> None:
        """Test duration property when end_time is present."""
        start = datetime.now()
        result = StepResult(description="Test", start_time=start, end_time=start)
        assert result.duration == 0.0


class TestContextHelpers:
    """Tests for context helper functions."""

    def setup_method(self) -> None:
        clear_steps()
        _get_context()["feature_id"] = None
        _get_context()["scenario_id"] = None
        _get_context()["in_specleft_test"] = False

    def test_clear_steps(self) -> None:
        """Test that clear_steps resets the steps list."""
        _get_context()["steps"] = [
            StepResult("step1", start_time=datetime.now()),
            StepResult("step2", start_time=datetime.now()),
        ]
        assert len(get_current_steps()) == 2

        clear_steps()
        assert len(get_current_steps()) == 0

    def test_get_current_steps_initializes_list(self) -> None:
        """Test that get_current_steps creates empty list if not present."""
        _get_context().pop("steps", None)
        steps = get_current_steps()
        assert steps == []
        assert "steps" in _get_context()

    def test_get_current_steps_returns_existing_list(self) -> None:
        """Test that get_current_steps returns existing list instance."""
        steps = [StepResult("step", start_time=datetime.now())]
        _get_context()["steps"] = steps
        assert get_current_steps() is steps

    def test_get_current_metadata_returns_values(self) -> None:
        """Test metadata helper returns current ids."""
        _get_context()["feature_id"] = "feat"
        _get_context()["scenario_id"] = "scenario"
        assert get_current_metadata() == {
            "feature_id": "feat",
            "scenario_id": "scenario",
        }

    def test_is_in_specleft_test_default_false(self) -> None:
        """Test that is_in_specleft_test returns False by default."""
        assert is_in_specleft_test() is False

    def test_reset_context_reinitializes(self) -> None:
        """Test reset context rebuilds defaults."""
        _get_context()["steps"] = [StepResult("step", start_time=datetime.now())]
        _get_context()["feature_id"] = "feat"
        _get_context()["scenario_id"] = "scenario"
        _get_context()["in_specleft_test"] = True

        _reset_context()
        ctx = _get_context()
        assert ctx["steps"] == []
        assert ctx["feature_id"] is None
        assert ctx["scenario_id"] is None
        assert ctx["in_specleft_test"] is False


class TestSpecleftDecorator:
    """Tests for @specleft decorator."""

    def test_decorator_stores_feature_id(self) -> None:
        """Test that decorator stores feature_id on function."""

        @specleft(feature_id="AUTH-001", scenario_id="login")
        def dummy_test() -> None:
            pass

        assert hasattr(dummy_test, "_specleft_feature_id")
        assert dummy_test._specleft_feature_id == "AUTH-001"

    def test_decorator_stores_scenario_id(self) -> None:
        """Test that decorator stores scenario_id on function."""

        @specleft(feature_id="AUTH-001", scenario_id="login-success")
        def dummy_test() -> None:
            pass

        assert hasattr(dummy_test, "_specleft_scenario_id")
        assert dummy_test._specleft_scenario_id == "login-success"

    def test_decorator_preserves_function_name(self) -> None:
        """Test that decorator preserves original function name."""

        @specleft(feature_id="AUTH-001", scenario_id="login")
        def test_user_login() -> None:
            """Test docstring."""
            pass

        assert test_user_login.__name__ == "test_user_login"
        assert test_user_login.__doc__ == "Test docstring."

    def test_decorator_resets_context(self) -> None:
        """Test that context is reset when test starts."""
        _get_context()["steps"] = [StepResult("old", start_time=datetime.now())]
        _get_context()["feature_id"] = "old"
        _get_context()["scenario_id"] = "old"
        _get_context()["in_specleft_test"] = False

        @specleft(feature_id="AUTH-001", scenario_id="login")
        def test_clears() -> None:
            assert get_current_steps() == []
            assert get_current_metadata() == {
                "feature_id": "AUTH-001",
                "scenario_id": "login",
            }
            assert is_in_specleft_test() is True

        test_clears()

    def test_decorator_clears_flag_after_test(self) -> None:
        """Test that in_specleft_test flag is cleared after execution."""

        @specleft(feature_id="AUTH-001", scenario_id="login")
        def test_clears_flag() -> None:
            pass

        test_clears_flag()
        assert is_in_specleft_test() is False

    def test_decorator_clears_flag_on_exception(self) -> None:
        """Test that in_specleft_test flag is cleared even on exception."""

        @specleft(feature_id="AUTH-001", scenario_id="login")
        def test_raises() -> None:
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            test_raises()

        assert is_in_specleft_test() is False

    def test_decorator_returns_function_result(self) -> None:
        """Test that decorator passes through function return value."""

        @specleft(feature_id="AUTH-001", scenario_id="login")
        def test_with_return() -> str:
            return "test result"

        result = test_with_return()
        assert result == "test result"

    def test_decorator_passes_args_and_kwargs(self) -> None:
        """Test that decorator passes arguments correctly."""

        @specleft(feature_id="AUTH-001", scenario_id="login")
        def test_with_args(a: int, b: str, c: float = 1.0) -> tuple[int, str, float]:
            return (a, b, c)

        result = test_with_args(1, "hello", c=2.5)
        assert result == (1, "hello", 2.5)

    def test_decorator_skip_adds_marker(self) -> None:
        """Test that skip=True applies pytest skip marker."""

        @specleft(
            feature_id="AUTH-001",
            scenario_id="login",
            skip=True,
            reason="Not implemented",
        )
        def test_skipped() -> None:
            pass

        marks = getattr(test_skipped, "pytestmark", [])
        skip_marks = [mark for mark in marks if mark.name == "skip"]
        assert skip_marks
        assert skip_marks[0].kwargs.get("reason") == "Not implemented"

    def test_decorator_skip_uses_default_reason(self) -> None:
        """Test skip uses default reason when omitted."""

        @specleft(feature_id="AUTH-001", scenario_id="login", skip=True)
        def test_skipped_default() -> None:
            pass

        marks = getattr(test_skipped_default, "pytestmark", [])
        skip_marks = [mark for mark in marks if mark.name == "skip"]
        assert skip_marks
        assert skip_marks[0].kwargs.get("reason") == "SpecLeft test skipped"


class TestStepContextManager:
    """Tests for specleft.step() context manager."""

    def setup_method(self) -> None:
        clear_steps()

    def test_step_records_description(self) -> None:
        """Test that step records the description."""
        with step("Given user is logged in"):
            pass

        steps = get_current_steps()
        assert len(steps) == 1
        assert steps[0].description == "Given user is logged in"

    def test_step_records_passed_status(self) -> None:
        """Test that successful step has passed status."""
        with step("Successful step"):
            pass

        steps = get_current_steps()
        assert steps[0].status == "passed"

    def test_step_records_failed_status_on_exception(self) -> None:
        """Test that step with exception has failed status."""
        with pytest.raises(ValueError), step("Failing step"):
            raise ValueError("Test error")

        steps = get_current_steps()
        assert steps[0].status == "failed"
        assert steps[0].error == "Test error"

    def test_step_records_timing(self) -> None:
        """Test that step records start and end times."""
        with step("Timed step"):
            time.sleep(0.01)

        steps = get_current_steps()
        assert steps[0].start_time is not None
        assert steps[0].end_time is not None
        assert steps[0].end_time >= steps[0].start_time

    def test_step_reraises_exception(self) -> None:
        """Test that step re-raises the original exception."""
        with (
            pytest.raises(RuntimeError, match="Original error"),
            step("Step that fails"),
        ):
            raise RuntimeError("Original error")

    def test_multiple_steps_recorded_in_order(self) -> None:
        """Test that multiple steps are recorded in execution order."""
        with step("Step 1"):
            pass
        with step("Step 2"):
            pass
        with step("Step 3"):
            pass

        steps = get_current_steps()
        assert len(steps) == 3
        assert steps[0].description == "Step 1"
        assert steps[1].description == "Step 2"
        assert steps[2].description == "Step 3"

    def test_step_with_dynamic_description(self) -> None:
        """Test step with f-string description."""
        username = "test@example.com"
        with step(f"User logs in with {username}"):
            pass

        steps = get_current_steps()
        assert steps[0].description == "User logs in with test@example.com"

    def test_step_skip_records_result(self) -> None:
        """Test that skipped steps are recorded."""
        with step("Skipped step", skip=True, reason="Not needed"):
            pass

        steps = get_current_steps()
        assert len(steps) == 1
        assert steps[0].status == "skipped"
        assert steps[0].skipped_reason == "Not needed"

    def test_step_skip_uses_default_reason(self) -> None:
        """Test skipped steps default reason."""
        with step("Skipped step", skip=True):
            pass

        steps = get_current_steps()
        assert steps[0].status == "skipped"
        assert steps[0].skipped_reason == "Step marked as skip"


class TestReusableStepDecorator:
    """Tests for @shared_step decorator."""

    def setup_method(self) -> None:
        clear_steps()
        _get_context()["in_specleft_test"] = False

    def test_reusable_step_stores_description(self) -> None:
        """Test that shared_step stores description on function."""

        @shared_step("User performs action")
        def user_action() -> None:
            pass

        assert hasattr(user_action, "_specleft_step_description")
        assert user_action._specleft_step_description == "User performs action"

    def test_reusable_step_traced_inside_specleft_test(self) -> None:
        """Test that shared step traces inside @specleft tests."""

        @shared_step("User clicks button")
        def click_button() -> str:
            return "clicked"

        @specleft(feature_id="UI-001", scenario_id="click-test")
        def test_click() -> str:
            return click_button()

        result = test_click()

        assert result == "clicked"
        steps = get_current_steps()
        assert len(steps) == 1
        assert steps[0].description == "User clicks button"

    def test_reusable_step_parameter_interpolation(self) -> None:
        """Test parameter interpolation in shared step description."""

        @shared_step("User logs in with {username}")
        def login(username: str, password: str) -> bool:
            return True

        @specleft(feature_id="AUTH-001", scenario_id="login")
        def test_login() -> None:
            login("admin@example.com", "secret")

        test_login()

        steps = get_current_steps()
        assert len(steps) == 1
        assert steps[0].description == "User logs in with admin@example.com"

    def test_reusable_step_multiple_parameters(self) -> None:
        """Test interpolation with multiple parameters."""

        @shared_step("Add {a} and {b} expecting {expected}")
        def add_numbers(a: int, b: int, expected: int) -> bool:
            return a + b == expected

        @specleft(feature_id="MATH-001", scenario_id="addition")
        def test_add() -> None:
            add_numbers(2, 3, expected=5)

        test_add()

        steps = get_current_steps()
        assert steps[0].description == "Add 2 and 3 expecting 5"

    def test_reusable_step_with_default_parameters(self) -> None:
        """Test interpolation with default parameters."""

        @shared_step("Navigate to {url} with timeout {timeout}")
        def navigate(url: str, timeout: int = 30) -> None:
            pass

        @specleft(feature_id="NAV-001", scenario_id="navigate")
        def test_nav() -> None:
            navigate("/dashboard")

        test_nav()

        steps = get_current_steps()
        assert steps[0].description == "Navigate to /dashboard with timeout 30"

    def test_reusable_step_invalid_interpolation_uses_original(self) -> None:
        """Test that invalid interpolation falls back to original description."""

        @shared_step("User does {nonexistent_param}")
        def do_action(value: str) -> None:
            pass

        @specleft(feature_id="TEST-001", scenario_id="test")
        def test_action() -> None:
            do_action("test")

        test_action()

        steps = get_current_steps()
        assert steps[0].description == "User does {nonexistent_param}"

    def test_reusable_step_no_args_fallback(self) -> None:
        """Test shared_step fallback when no parameters are provided."""

        @shared_step("User performs {action}")
        def do_action() -> None:
            pass

        @specleft(feature_id="TEST-002", scenario_id="fallback")
        def test_action() -> None:
            do_action()

        test_action()

        steps = get_current_steps()
        assert steps[0].description == "User performs {action}"

    def test_reusable_step_records_duration(self) -> None:
        """Test shared_step records duration and ends timing."""

        @shared_step("Quick action")
        def do_action() -> None:
            time.sleep(0.01)

        @specleft(feature_id="TEST-003", scenario_id="timed")
        def test_action() -> None:
            do_action()

        test_action()

        steps = get_current_steps()
        assert steps[0].duration >= 0


class TestContextInitialization:
    """Tests for module initialization behavior."""

    def test_context_initialized_on_first_call(self) -> None:
        """Test _get_context initializes thread-local data."""
        _reset_context()
        context = _get_context()
        assert context["steps"] == []
        assert context["feature_id"] is None
        assert context["scenario_id"] is None
        assert context["in_specleft_test"] is False

    def test_get_context_rebuilds_when_missing(self) -> None:
        """Test _get_context rebuilds when data missing."""
        original = decorators._test_context
        decorators._test_context = decorators._SpecleftThreadContext()
        try:
            assert not hasattr(decorators._test_context, "data")
            context = decorators._get_context()
            assert context["steps"] == []
            assert context["feature_id"] is None
        finally:
            decorators._test_context = original

    def test_module_reload_resets_exports(self) -> None:
        """Test reloading module reinitializes exports."""
        module = importlib.reload(decorators)
        assert module.specleft
        assert module.step
        assert module.shared_step

    def test_reusable_step_preserves_function_name(self) -> None:
        """Test that shared_step preserves original function name."""

        @shared_step("Perform action")
        def perform_important_action() -> None:
            """Important action docstring."""
            pass

        assert perform_important_action.__name__ == "perform_important_action"
        assert perform_important_action.__doc__ == "Important action docstring."

    def test_reusable_step_returns_value(self) -> None:
        """Test that shared step returns function's return value."""

        @shared_step("Get user data")
        def get_user() -> dict:
            return {"id": 1, "name": "Test"}

        @specleft(feature_id="USER-001", scenario_id="get-user")
        def test_get_user() -> dict:
            return get_user()

        result = test_get_user()

        assert result == {"id": 1, "name": "Test"}

    def test_reusable_step_propagates_exceptions(self) -> None:
        """Test that shared step propagates exceptions."""

        @shared_step("Failing action")
        def failing_action() -> None:
            raise RuntimeError("Action failed")

        @specleft(feature_id="ERR-001", scenario_id="error-test")
        def test_failure() -> None:
            failing_action()

        with pytest.raises(RuntimeError, match="Action failed"):
            test_failure()

        steps = get_current_steps()
        assert len(steps) == 1
        assert steps[0].status == "failed"
        assert "Action failed" in steps[0].error

    def test_multiple_reusable_steps_in_test(self) -> None:
        """Test multiple shared steps in one test."""

        @shared_step("Step A with {value}")
        def step_a(value: str) -> None:
            pass

        @shared_step("Step B with {value}")
        def step_b(value: str) -> None:
            pass

        @specleft(feature_id="MULTI-001", scenario_id="multi-step")
        def test_multi() -> None:
            step_a("first")
            step_b("second")

        test_multi()

        steps = get_current_steps()
        assert len(steps) == 2
        assert steps[0].description == "Step A with first"
        assert steps[1].description == "Step B with second"


class TestThreadSafety:
    """Tests for thread safety of step collection."""

    def test_steps_are_thread_local(self) -> None:
        """Test that steps are isolated between threads."""
        results: dict[int, list[str]] = {}

        def worker(thread_id: int) -> None:
            clear_steps()

            @specleft(feature_id="THREAD-001", scenario_id="thread-test")
            def thread_test() -> None:
                with step(f"Thread {thread_id} step"):
                    time.sleep(0.01)

            thread_test()
            results[thread_id] = [s.description for s in get_current_steps()]

        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        for thread_id, steps in results.items():
            assert len(steps) == 1
            assert f"Thread {thread_id}" in steps[0]

    def test_in_specleft_test_flag_is_thread_local(self) -> None:
        """Test that in_specleft_test flag is thread-local."""
        flags_during_test: dict[int, bool] = {}

        def worker(thread_id: int) -> None:
            @specleft(feature_id="THREAD-001", scenario_id="flag-test")
            def thread_test() -> None:
                flags_during_test[thread_id] = is_in_specleft_test()
                time.sleep(0.01)

            thread_test()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, i) for i in range(5)]
            concurrent.futures.wait(futures)

        for thread_id in range(5):
            assert flags_during_test[thread_id] is True

        assert is_in_specleft_test() is False


class TestCombinedUsage:
    """Tests for combined usage of decorators and context managers."""

    def setup_method(self) -> None:
        clear_steps()

    def test_manual_and_reusable_steps_together(self) -> None:
        """Test mixing manual step() with shared_step()."""

        @shared_step("Setup user {username}")
        def setup_user(username: str) -> None:
            pass

        @specleft(feature_id="MIXED-001", scenario_id="mixed-test")
        def test_mixed() -> None:
            with step("Given the system is ready"):
                pass
            setup_user("testuser")
            with step("Then verify results"):
                pass

        test_mixed()

        steps = get_current_steps()
        assert len(steps) == 3
        assert steps[0].description == "Given the system is ready"
        assert steps[1].description == "Setup user testuser"
        assert steps[2].description == "Then verify results"

    def test_reusable_step_called_from_another_reusable_step(self) -> None:
        """Test shared step calling another shared step."""

        @shared_step("Low level action: {action}")
        def low_level(action: str) -> None:
            pass

        @shared_step("High level workflow")
        def high_level() -> None:
            low_level("step 1")
            low_level("step 2")

        @specleft(feature_id="NESTED-001", scenario_id="nested-shared")
        def test_nested() -> None:
            high_level()

        test_nested()

        steps = get_current_steps()
        assert len(steps) == 3
        assert steps[0].description == "Low level action: step 1"
        assert steps[1].description == "Low level action: step 2"
        assert steps[2].description == "High level workflow"
