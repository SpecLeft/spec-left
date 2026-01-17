"""Tests for specleft.spec_differ."""

from __future__ import annotations

from specleft.schema import ScenarioSpec, SpecStep, StepType
from specleft.spec_differ import SpecDiffer, StepDiff


def _build_scenario(step_descriptions: list[str]) -> ScenarioSpec:
    steps = [
        SpecStep(type=StepType.GIVEN, description=desc) for desc in step_descriptions
    ]
    return ScenarioSpec(
        scenario_id="sample-scenario",
        name="Sample Scenario",
        steps=steps,
    )


def test_diff_scenario_no_changes() -> None:
    spec = _build_scenario(["alpha", "beta"])
    differ = SpecDiffer()

    diffs = differ.diff_scenario(spec, ["Given alpha", "Given beta"])

    assert diffs == []


def test_diff_scenario_added_step() -> None:
    spec = _build_scenario(["alpha", "beta", "gamma"])
    differ = SpecDiffer()

    diffs = differ.diff_scenario(spec, ["Given alpha", "Given beta"])

    assert StepDiff(type="added", step_description="Given gamma", new_index=2) in diffs


def test_diff_scenario_removed_step() -> None:
    spec = _build_scenario(["alpha", "beta"])
    differ = SpecDiffer()

    diffs = differ.diff_scenario(spec, ["Given alpha", "Given beta", "Given delta"])

    assert (
        StepDiff(type="removed", step_description="Given delta", old_index=2) in diffs
    )


def test_diff_scenario_modified_step() -> None:
    spec = _build_scenario(["alpha", "beta"])
    differ = SpecDiffer()

    diffs = differ.diff_scenario(spec, ["Given alpha", "Given beta old"])

    assert (
        StepDiff(
            type="modified",
            step_description="Given beta",
            new_index=1,
            old_index=1,
        )
        in diffs
    )


def test_diff_scenario_reordered_steps_are_moves() -> None:
    spec = _build_scenario(["alpha", "beta", "gamma"])
    differ = SpecDiffer()

    diffs = differ.diff_scenario(
        spec,
        ["Given beta", "Given alpha", "Given gamma"],
    )

    assert (
        StepDiff(
            type="moved",
            step_description="Given beta",
            new_index=1,
            old_index=0,
        )
        in diffs
    )
