"""Tests for specleft.test_revisor."""

from __future__ import annotations

from specleft.spec_differ import StepDiff
from specleft.skeleton_revisor import TestFunctionRevisor


def _build_source(steps: list[str]) -> str:
    lines = [
        "from specleft import specleft",
        "",
        '@specleft(feature_id="auth", scenario_id="login-success")',
        "def test_login_success():",
        '    """Login success"""',
    ]
    for step in steps:
        lines.append(f'    with specleft.step("{step}"):')
        lines.append("        pass")
        lines.append("")
    return "\n".join(lines)


def test_revisor_adds_step() -> None:
    source = _build_source(["Given one", "When two"])
    revisor = TestFunctionRevisor(source)
    plan = revisor.build_revision_plan(
        "login-success",
        [StepDiff(type="added", step_description="Then three", new_index=2)],
    )

    updated = revisor.revise_test_file(plan)

    assert 'with specleft.step("Then three"):' in updated


def test_revisor_skips_removed_step() -> None:
    source = _build_source(["Given one", "When two", "Then three"])
    revisor = TestFunctionRevisor(source)
    plan = revisor.build_revision_plan(
        "login-success",
        [StepDiff(type="removed", step_description="When two", old_index=1)],
    )

    updated = revisor.revise_test_file(plan)
    assert 'with specleft.step("When two", skip=True, reason="Removed from spec"):' in updated


def test_revisor_marks_modified_step() -> None:
    source = _build_source(["Given one", "When two"])
    revisor = TestFunctionRevisor(source)
    plan = revisor.build_revision_plan(
        "login-success",
        [
            StepDiff(
                type="modified",
                step_description="When two updated",
                new_index=1,
                old_index=1,
            )
        ],
    )

    updated = revisor.revise_test_file(plan)

    assert "Modified in spec" in updated
    assert "When two" in updated
    assert "When two updated" in updated


def test_revisor_missing_scenario_returns_original() -> None:
    source = _build_source(["Given one", "When two"])
    revisor = TestFunctionRevisor(source)
    plan = revisor.build_revision_plan(
        "missing-scenario",
        [StepDiff(type="added", step_description="Then three", new_index=2)],
    )

    updated = revisor.revise_test_file(plan)

    assert updated == source


def test_revisor_inserts_condition_in_middle() -> None:
    source = _build_source(["Given one", "When two", "Then three"])
    revisor = TestFunctionRevisor(source)
    plan = revisor.build_revision_plan(
        "login-success",
        [StepDiff(type="added", step_description="And four", new_index=1)],
    )

    updated = revisor.revise_test_file(plan)

    lines = updated.splitlines()
    for index, line in enumerate(lines):
        if 'with specleft.step("' in line:
            next_index = index + 1
            while next_index < len(lines) and not lines[next_index].strip():
                next_index += 1
            assert next_index < len(lines)
            assert lines[next_index].strip().startswith("pass")
