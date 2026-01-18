"""SpecLeft Decorators.

Provides the @specleft decorator and step() context manager for test functions.
"""

from __future__ import annotations

import functools
import inspect
import threading
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypedDict, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class StepResult:
    """Result of a single test step execution."""

    description: str
    status: str = "passed"
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    error: str | None = None
    skipped_reason: str | None = None

    @property
    def duration(self) -> float:
        """Return step duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class _SpecleftContext(TypedDict):
    steps: list[StepResult]
    feature_id: str | None
    scenario_id: str | None
    in_specleft_test: bool


class _SpecleftThreadContext(threading.local):
    data: _SpecleftContext


_test_context = _SpecleftThreadContext()


def _new_context() -> _SpecleftContext:
    return {
        "steps": [],
        "feature_id": None,
        "scenario_id": None,
        "in_specleft_test": False,
    }


def _get_context() -> _SpecleftContext:
    if not hasattr(_test_context, "data"):
        _test_context.data = _new_context()
    return _test_context.data


def _reset_context() -> None:
    _test_context.data = _new_context()


def get_current_steps() -> list[StepResult]:
    """Return current step results for this test execution."""
    ctx = _get_context()
    steps = ctx.get("steps")
    if steps is None:
        ctx["steps"] = []
        return ctx["steps"]
    return steps


def clear_steps() -> None:
    """Clear current step results for this test execution."""
    _get_context()["steps"] = []


def get_current_metadata() -> dict[str, str | None]:
    """Return current feature/scenario metadata."""
    ctx = _get_context()
    return {
        "feature_id": ctx.get("feature_id"),
        "scenario_id": ctx.get("scenario_id"),
    }


def is_in_specleft_test() -> bool:
    """Return True when inside a @specleft test."""
    return bool(_get_context().get("in_specleft_test", False))


class SpecleftDecorator:
    """Main decorator class for marking tests with SpecLeft metadata."""

    def __call__(
        self,
        feature_id: str,
        scenario_id: str,
        skip: bool = False,
        reason: str | None = None,
    ) -> Callable[[F], F]:
        def decorator(func: F) -> F:
            func._specleft_feature_id = feature_id  # type: ignore[attr-defined]
            func._specleft_scenario_id = scenario_id  # type: ignore[attr-defined]

            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                _reset_context()
                ctx = _get_context()
                ctx["feature_id"] = feature_id
                ctx["scenario_id"] = scenario_id
                ctx["in_specleft_test"] = True
                try:
                    return func(*args, **kwargs)
                finally:
                    ctx["in_specleft_test"] = False

            if skip:
                skip_reason = reason or "SpecLeft test skipped"
                import pytest

                return cast(F, pytest.mark.skip(reason=skip_reason)(wrapper))

            return cast(F, wrapper)

        return decorator

    @staticmethod
    @contextmanager
    def step(
        description: str,
        skip: bool = False,
        reason: str | None = None,
    ) -> Generator[None, None, None]:
        """Context manager for test steps."""
        ctx = _get_context()
        step_result = StepResult(description=description, start_time=datetime.now())

        if skip:
            step_result.status = "skipped"
            step_result.skipped_reason = reason or "Step marked as skip"
            step_result.end_time = datetime.now()
            ctx["steps"].append(step_result)
            yield
            return

        try:
            yield
            step_result.status = "passed"
        except Exception as exc:
            step_result.status = "failed"
            step_result.error = str(exc)
            raise
        finally:
            step_result.end_time = datetime.now()
            ctx["steps"].append(step_result)

    @staticmethod
    def shared_step(description: str) -> Callable[[F], F]:
        """Decorator for creating shared step functions."""

        def decorator(func: F) -> F:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    sig = inspect.signature(func)
                    bound = sig.bind(*args, **kwargs)
                    bound.apply_defaults()
                    formatted_desc = description.format(**bound.arguments)
                except (KeyError, IndexError, ValueError, TypeError):
                    formatted_desc = description

                ctx = _get_context()
                step_result = StepResult(
                    description=formatted_desc, start_time=datetime.now()
                )

                try:
                    result = func(*args, **kwargs)
                    step_result.status = "passed"
                    return result
                except Exception as exc:
                    step_result.status = "failed"
                    step_result.error = str(exc)
                    raise
                finally:
                    step_result.end_time = datetime.now()
                    ctx["steps"].append(step_result)

            wrapper._specleft_reusable_step = True  # type: ignore[attr-defined]
            wrapper._specleft_step_description = description  # type: ignore[attr-defined]
            return wrapper  # type: ignore[return-value]

        return decorator


specleft = SpecleftDecorator()
step = specleft.step
shared_step = specleft.shared_step


__all__ = [
    "StepResult",
    "clear_steps",
    "get_current_metadata",
    "get_current_steps",
    "is_in_specleft_test",
    "shared_step",
    "specleft",
    "step",
]
