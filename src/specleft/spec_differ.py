"""SpecLeft Spec Differ - detects changes between specs and tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from specleft.schema import ScenarioSpec


@dataclass(frozen=True)
class StepDiff:
    """Represents a difference in steps."""

    type: Literal["added", "removed", "modified", "moved"]
    step_description: str
    new_index: int | None = None
    old_index: int | None = None


class SpecDiffer:
    """Compares spec steps with test steps."""

    def diff_scenario(
        self, spec: ScenarioSpec, test_steps: Sequence[str]
    ) -> list[StepDiff]:
        """Find differences between spec steps and test steps."""
        diffs: list[StepDiff] = []
        spec_steps = [
            f"{step.type.value.capitalize()} {step.description}" for step in spec.steps
        ]
        test_steps_list = list(test_steps)
        if not spec_steps and not test_steps_list:
            return diffs

        modified_spec_indices: set[int] = set()
        modified_test_indices: set[int] = set()
        min_len = min(len(spec_steps), len(test_steps_list))
        for index in range(min_len):
            spec_step = spec_steps[index]
            test_step = test_steps_list[index]
            if spec_step == test_step:
                continue
            if spec_step not in test_steps_list and test_step not in spec_steps:
                diffs.append(
                    StepDiff(
                        type="modified",
                        step_description=spec_step,
                        new_index=index,
                        old_index=index,
                    )
                )
                modified_spec_indices.add(index)
                modified_test_indices.add(index)

        spec_candidates = [
            (index, step)
            for index, step in enumerate(spec_steps)
            if index not in modified_spec_indices
        ]
        test_candidates = [
            (index, step)
            for index, step in enumerate(test_steps_list)
            if index not in modified_test_indices
        ]

        spec_values = [step for _, step in spec_candidates]
        test_values = [step for _, step in test_candidates]
        lcs_pairs = self._lcs_indices(spec_values, test_values)

        matched_spec_indices = {
            spec_candidates[spec_index][0] for spec_index, _ in lcs_pairs
        }
        matched_test_indices = {
            test_candidates[test_index][0] for _, test_index in lcs_pairs
        }

        unmatched_test_by_desc: dict[str, list[int]] = {}
        for index, step in enumerate(test_steps_list):
            if index in matched_test_indices or index in modified_test_indices:
                continue
            unmatched_test_by_desc.setdefault(step, []).append(index)

        for spec_index, spec_step in enumerate(spec_steps):
            if spec_index in matched_spec_indices or spec_index in modified_spec_indices:
                continue
            available = unmatched_test_by_desc.get(spec_step)
            if available:
                old_index = available.pop(0)
                diffs.append(
                    StepDiff(
                        type="moved",
                        step_description=spec_step,
                        new_index=spec_index,
                        old_index=old_index,
                    )
                )
                if not available:
                    unmatched_test_by_desc.pop(spec_step, None)
            else:
                diffs.append(
                    StepDiff(
                        type="added",
                        step_description=spec_step,
                        new_index=spec_index,
                    )
                )

        for step_description, indices in unmatched_test_by_desc.items():
            for old_index in indices:
                diffs.append(
                    StepDiff(
                        type="removed",
                        step_description=step_description,
                        old_index=old_index,
                    )
                )

        return diffs

    @staticmethod
    def _lcs_indices(
        spec_values: Sequence[str], test_values: Sequence[str]
    ) -> list[tuple[int, int]]:
        """Compute LCS index pairs for two sequences."""
        spec_len = len(spec_values)
        test_len = len(test_values)
        table = [[0] * (test_len + 1) for _ in range(spec_len + 1)]

        for i in range(spec_len - 1, -1, -1):
            for j in range(test_len - 1, -1, -1):
                if spec_values[i] == test_values[j]:
                    table[i][j] = 1 + table[i + 1][j + 1]
                else:
                    table[i][j] = max(table[i + 1][j], table[i][j + 1])

        i = 0
        j = 0
        pairs: list[tuple[int, int]] = []
        while i < spec_len and j < test_len:
            if spec_values[i] == test_values[j]:
                pairs.append((i, j))
                i += 1
                j += 1
            elif table[i + 1][j] >= table[i][j + 1]:
                i += 1
            else:
                j += 1

        return pairs
