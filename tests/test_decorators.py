"""Tests for specleft.decorators module."""

from __future__ import annotations

import concurrent.futures
import threading
import time
from datetime import datetime

import pytest

from specleft.decorators import (
    StepResult,
    _test_context,
    clear_steps,
    get_current_steps,
    is_in_specleft_test,
    reusable_step,
    specleft,
    step,
)


class TestStepResult:
    """Tests for StepResult dataclass."""

    def test_minimal_step_result(self) -> None:
        """Test creating StepResult with required fields only."""
        now = datetime.now()
        result = StepResult(
            description="Test step",
            status="passed",
            start_time=now,
        )
        assert result.description == "Test step"
        assert result.status == "passed"
        assert result.start_time == now
        assert result.end_time is None
        assert result.error is None

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
        )
        assert result.description == "Failed step"
        assert result.status == "failed"
        assert result.end_time == end
        assert result.error == "Something went wrong"


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_clear_steps(self) -> None:
        """Test that clear_steps resets the steps list."""
        # Add some steps
        _test_context.steps = [
            StepResult("step1", "passed", datetime.now()),
            StepResult("step2", "passed", datetime.now()),
        ]
        assert len(get_current_steps()) == 2

        clear_steps()
        assert len(get_current_steps()) == 0

    def test_get_current_steps_initializes_list(self) -> None:
        """Test that get_current_steps creates empty list if not present."""
        # Remove steps attribute if present
        if hasattr(_test_context, "steps"):
            delattr(_test_context, "steps")

        steps = get_current_steps()
        assert steps == []
        assert hasattr(_test_context, "steps")

    def test_is_in_specleft_test_default_false(self) -> None:
        """Test that is_in_specleft_test returns False by default."""
        # Remove attribute if present
        if hasattr(_test_context, "in_specleft_test"):
            delattr(_test_context, "in_specleft_test")

        assert is_in_specleft_test() is False


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

    def test_decorator_clears_steps_on_entry(self) -> None:
        """Test that steps are cleared when test starts."""
        # Pre-populate steps
        _test_context.steps = [StepResult("old", "passed", datetime.now())]

        @specleft(feature_id="AUTH-001", scenario_id="login")
        def test_clears() -> None:
            # Steps should be empty at start
            assert len(get_current_steps()) == 0

        test_clears()

    def test_decorator_sets_in_specleft_test_flag(self) -> None:
        """Test that in_specleft_test flag is set during execution."""
        flag_during_test = None

        @specleft(feature_id="AUTH-001", scenario_id="login")
        def test_flag() -> None:
            nonlocal flag_during_test
            flag_during_test = is_in_specleft_test()

        # Before test
        _test_context.in_specleft_test = False

        test_flag()

        # During test, flag should have been True
        assert flag_during_test is True

    def test_decorator_clears_flag_after_test(self) -> None:
        """Test that in_specleft_test flag is cleared after execution."""

        @specleft(feature_id="AUTH-001", scenario_id="login")
        def test_clears_flag() -> None:
            pass

        test_clears_flag()

        # After test, flag should be False
        assert is_in_specleft_test() is False

    def test_decorator_clears_flag_on_exception(self) -> None:
        """Test that in_specleft_test flag is cleared even on exception."""

        @specleft(feature_id="AUTH-001", scenario_id="login")
        def test_raises() -> None:
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            test_raises()

        # Flag should still be cleared
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
        def test_with_args(a: int, b: str, c: float = 1.0) -> tuple:
            return (a, b, c)

        result = test_with_args(1, "hello", c=2.5)
        assert result == (1, "hello", 2.5)


class TestStepContextManager:
    """Tests for specleft.step() context manager."""

    def setup_method(self) -> None:
        """Clear steps before each test."""
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
            time.sleep(0.01)  # Small delay to ensure measurable duration

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

    def test_step_yields_step_result(self) -> None:
        """Test that step context manager yields StepResult."""
        with step("Test step") as result:
            assert isinstance(result, StepResult)
            assert result.description == "Test step"

    def test_nested_steps(self) -> None:
        """Test that nested steps are all recorded."""
        with step("Outer step"), step("Inner step"):
            pass

        steps = get_current_steps()
        # Both steps should be recorded (inner first due to exit order)
        assert len(steps) == 2


class TestReusableStepDecorator:
    """Tests for @reusable_step decorator."""

    def setup_method(self) -> None:
        """Clear steps and reset flag before each test."""
        clear_steps()
        _test_context.in_specleft_test = False

    def test_reusable_step_stores_description(self) -> None:
        """Test that reusable_step stores description on function."""

        @reusable_step("User performs action")
        def user_action() -> None:
            pass

        assert hasattr(user_action, "_specleft_step_description")
        assert user_action._specleft_step_description == "User performs action"

    def test_reusable_step_not_traced_outside_specleft_test(self) -> None:
        """Test that reusable step doesn't trace outside @specleft tests."""

        @reusable_step("User clicks button")
        def click_button() -> str:
            return "clicked"

        result = click_button()

        # Should return result normally
        assert result == "clicked"
        # Should NOT record step
        assert len(get_current_steps()) == 0

    def test_reusable_step_traced_inside_specleft_test(self) -> None:
        """Test that reusable step traces inside @specleft tests."""

        @reusable_step("User clicks button")
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
        """Test parameter interpolation in reusable step description."""

        @reusable_step("User logs in with {username}")
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

        @reusable_step("Add {a} and {b} expecting {expected}")
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

        @reusable_step("Navigate to {url} with timeout {timeout}")
        def navigate(url: str, timeout: int = 30) -> None:
            pass

        @specleft(feature_id="NAV-001", scenario_id="navigate")
        def test_nav() -> None:
            navigate("/dashboard")  # Uses default timeout

        test_nav()

        steps = get_current_steps()
        assert steps[0].description == "Navigate to /dashboard with timeout 30"

    def test_reusable_step_invalid_interpolation_uses_original(self) -> None:
        """Test that invalid interpolation falls back to original description."""

        @reusable_step("User does {nonexistent_param}")
        def do_action(value: str) -> None:
            pass

        @specleft(feature_id="TEST-001", scenario_id="test")
        def test_action() -> None:
            do_action("test")

        test_action()

        steps = get_current_steps()
        # Should use original description when interpolation fails
        assert steps[0].description == "User does {nonexistent_param}"

    def test_reusable_step_preserves_function_name(self) -> None:
        """Test that reusable_step preserves original function name."""

        @reusable_step("Perform action")
        def perform_important_action() -> None:
            """Important action docstring."""
            pass

        assert perform_important_action.__name__ == "perform_important_action"
        assert perform_important_action.__doc__ == "Important action docstring."

    def test_reusable_step_returns_value(self) -> None:
        """Test that reusable step returns function's return value."""

        @reusable_step("Get user data")
        def get_user() -> dict:
            return {"id": 1, "name": "Test"}

        @specleft(feature_id="USER-001", scenario_id="get-user")
        def test_get_user() -> dict:
            return get_user()

        result = test_get_user()

        assert result == {"id": 1, "name": "Test"}

    def test_reusable_step_propagates_exceptions(self) -> None:
        """Test that reusable step propagates exceptions."""

        @reusable_step("Failing action")
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
        """Test multiple reusable steps in one test."""

        @reusable_step("Step A with {value}")
        def step_a(value: str) -> None:
            pass

        @reusable_step("Step B with {value}")
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
                    time.sleep(0.01)  # Simulate work

            thread_test()
            results[thread_id] = [s.description for s in get_current_steps()]

        # Run multiple threads concurrently
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Each thread should have only its own step
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

        # All threads should have had True during their test
        for thread_id in range(5):
            assert flags_during_test[thread_id] is True

        # After all tests, flag should be False in main thread
        assert is_in_specleft_test() is False


class TestCombinedUsage:
    """Tests for combined usage of decorators and context managers."""

    def setup_method(self) -> None:
        """Clear steps before each test."""
        clear_steps()

    def test_manual_and_reusable_steps_together(self) -> None:
        """Test mixing manual step() with reusable_step()."""

        @reusable_step("Setup user {username}")
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
        """Test reusable step calling another reusable step."""

        @reusable_step("Low level action: {action}")
        def low_level(action: str) -> None:
            pass

        @reusable_step("High level workflow")
        def high_level() -> None:
            low_level("step 1")
            low_level("step 2")

        @specleft(feature_id="NESTED-001", scenario_id="nested-reusable")
        def test_nested() -> None:
            high_level()

        test_nested()

        steps = get_current_steps()
        # All steps should be recorded
        assert len(steps) == 3
        assert steps[0].description == "Low level action: step 1"
        assert steps[1].description == "Low level action: step 2"
        assert steps[2].description == "High level workflow"
