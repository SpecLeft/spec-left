"""SpecLeft Test Revisor - updates test files based on spec changes."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Sequence

from specleft.spec_differ import StepDiff


@dataclass(frozen=True)
class RevisionPlan:
    """Plan for revising a scenario's steps."""

    scenario_id: str
    additions: tuple[StepDiff, ...]
    removals: tuple[StepDiff, ...]
    modifications: tuple[StepDiff, ...]
    moves: tuple[StepDiff, ...]

    @property
    def has_changes(self) -> bool:
        return bool(self.additions or self.removals or self.modifications or self.moves)


@dataclass
class StepBlock:
    description: str | None
    lines: list[str]
    original_index: int | None


class TestFunctionRevisor:
    """Revises test functions based on spec diffs."""

    def __init__(self, source: str):
        self.source = source
        self.lines = source.splitlines()

    def build_revision_plan(
        self, scenario_id: str, diffs: Sequence[StepDiff]
    ) -> RevisionPlan:
        """Build a plan for revising a scenario based on diffs."""
        additions = tuple(diff for diff in diffs if diff.type == "added")
        removals = tuple(diff for diff in diffs if diff.type == "removed")
        modifications = tuple(diff for diff in diffs if diff.type == "modified")
        moves = tuple(diff for diff in diffs if diff.type == "moved")
        return RevisionPlan(
            scenario_id=scenario_id,
            additions=additions,
            removals=removals,
            modifications=modifications,
            moves=moves,
        )

    def revise_test_file(self, plan: RevisionPlan) -> str:
        """Apply revisions to a test file."""
        if not plan.has_changes:
            return self.source

        updated_lines = list(self.lines)
        scenario_range = self._find_scenario_range(updated_lines, plan.scenario_id)
        if scenario_range is None:
            return self.source

        start, end = scenario_range
        scenario_lines = updated_lines[start:end]
        step_block = self._find_step_block(scenario_lines)
        if step_block is None:
            return self.source

        step_start, step_end, indent = step_block
        step_block_lines = scenario_lines[step_start:step_end]
        step_blocks = self._split_step_blocks(step_block_lines)

        for diff in sorted(plan.moves, key=lambda item: item.new_index or 0):
            step_blocks = self._move_step(step_blocks, diff)

        for diff in sorted(
            plan.removals, key=lambda item: item.old_index or 0, reverse=True
        ):
            step_blocks = self._skip_step(step_blocks, diff)

        for diff in sorted(plan.modifications, key=lambda item: item.old_index or 0):
            step_blocks = self._mark_modified(step_blocks, diff)

        for diff in sorted(plan.modifications, key=lambda item: item.new_index or 0):
            step_blocks = self._insert_modified_step(step_blocks, diff, indent)

        for diff in sorted(plan.additions, key=lambda item: item.new_index or 0):
            step_blocks = self._add_step(step_blocks, diff, indent)

        scenario_lines[step_start:step_end] = self._flatten_step_blocks(step_blocks)
        updated_lines[start:end] = scenario_lines
        return "\n".join(updated_lines)

    def _find_scenario_range(
        self, lines: list[str], scenario_id: str
    ) -> tuple[int, int] | None:
        decorator_index: int | None = None
        for index, line in enumerate(lines):
            if f'scenario_id="{scenario_id}"' in line:
                decorator_index = index
                break
        if decorator_index is None:
            return None

        function_index: int | None = None
        for index in range(decorator_index, len(lines)):
            if lines[index].lstrip().startswith("def test_"):
                function_index = index
                break
        if function_index is None:
            return None

        base_indent = len(lines[function_index]) - len(lines[function_index].lstrip())
        for index in range(function_index + 1, len(lines)):
            line = lines[index]
            if line.strip() and (len(line) - len(line.lstrip()) <= base_indent):
                return function_index, index
        return function_index, len(lines)

    def _find_step_block(
        self, scenario_lines: list[str], base_indent: int = 4
    ) -> tuple[int, int, str] | None:
        step_start: int | None = None
        step_indent = " " * base_indent
        for index, line in enumerate(scenario_lines):
            if "specleft.step(" in line:
                step_indent = line[: len(line) - len(line.lstrip())]
                step_start = index
                break
        if step_start is None:
            return None

        step_end = len(scenario_lines)
        for index in range(step_start + 1, len(scenario_lines)):
            line = scenario_lines[index]
            if line.strip() and not line.startswith(step_indent):
                step_end = index
                break
        return step_start, step_end, step_indent

    @staticmethod
    def _parse_step_description(line: str) -> str | None:
        stripped = line.strip()
        if not stripped.startswith("with specleft.step("):
            return None
        match = re.search(r"specleft\.step\(\s*\"([^\"]+)\"", stripped)
        if match:
            return match.group(1)
        match = re.search(r"specleft\.step\(\s*'([^']+)'", stripped)
        if match:
            return match.group(1)
        return None

    @classmethod
    def _skip_step(cls, blocks: list[StepBlock], diff: StepDiff) -> list[StepBlock]:
        index = cls._find_block_index(blocks, diff)
        if index is None:
            return blocks
        block = blocks[index]
        line = block.lines[0]
        if "skip=True" in line:
            return blocks
        replacement = line.rstrip()
        if replacement.endswith(":"):
            replacement = replacement[:-2]
        replacement = f'{replacement}, skip=True, reason="Removed from spec"):'
        block.lines[0] = replacement
        return blocks

    @classmethod
    def _mark_modified(cls, blocks: list[StepBlock], diff: StepDiff) -> list[StepBlock]:
        index = cls._find_block_index(blocks, diff)
        if index is None:
            return blocks
        block = blocks[index]
        line = block.lines[0].rstrip()
        if line.endswith(":"):
            line = line[:-1]
        if "skip=True" not in line:
            line = f'{line}, skip=True, reason="Modified in spec")'
        block.lines[0] = f"{line}:"
        return blocks

    @classmethod
    def _add_step(
        cls, blocks: list[StepBlock], diff: StepDiff, indent: str
    ) -> list[StepBlock]:
        description = diff.step_description
        if '"' in description and "'" not in description:
            description = description.replace('"', "'")

        step_literal = json.dumps(description)
        line = f"with specleft.step({step_literal}):"

        addition = StepBlock(
            description=description,
            lines=[
                f'{indent}{line}',
                f"{indent}    assert not True  # TODO: Skeleton step - Implement logic here",
                "",
            ],
            original_index=None,
        )

        if diff.new_index is None:
            blocks.append(addition)
            return blocks

        active_positions = cls._active_positions(blocks)
        if diff.new_index >= len(active_positions):
            blocks.append(addition)
            return blocks

        blocks.insert(active_positions[diff.new_index], addition)
        return blocks

    @classmethod
    def _insert_modified_step(
        cls, blocks: list[StepBlock], diff: StepDiff, indent: str
    ) -> list[StepBlock]:
        if diff.new_index is None:
            return blocks
        for block in blocks:
            if block.description == diff.step_description:
                return blocks
        added = StepDiff(
            type="added",
            step_description=diff.step_description,
            new_index=diff.new_index,
        )
        return cls._add_step(blocks, added, indent)

    @classmethod
    def _move_step(cls, blocks: list[StepBlock], diff: StepDiff) -> list[StepBlock]:
        if diff.old_index is None:
            return blocks
        index = cls._find_block_index(blocks, diff)
        if index is None:
            return blocks
        block = blocks.pop(index)
        new_index = diff.new_index
        if new_index is None:
            blocks.append(block)
            return blocks
        active_positions = cls._active_positions(blocks)
        if new_index >= len(active_positions):
            blocks.append(block)
            return blocks
        blocks.insert(active_positions[new_index], block)
        return blocks

    @classmethod
    def _find_block_index(
        cls, blocks: list[StepBlock], diff: StepDiff
    ) -> int | None:
        if diff.old_index is not None:
            for index, block in enumerate(blocks):
                if block.original_index == diff.old_index:
                    return index
        for index, block in enumerate(blocks):
            if block.description == diff.step_description:
                return index
        return None

    @classmethod
    def _split_step_blocks(cls, block_lines: list[str]) -> list[StepBlock]:
        blocks: list[StepBlock] = []
        current_lines: list[str] = []
        current_description: str | None = None
        step_index = 0
        for line in block_lines:
            description = cls._parse_step_description(line)
            if description is not None:
                if current_lines:
                    blocks.append(
                        StepBlock(
                            description=current_description,
                            lines=current_lines,
                            original_index=step_index - 1,
                        )
                    )
                current_lines = [line]
                current_description = description
                step_index += 1
            else:
                current_lines.append(line)

        if current_lines:
            blocks.append(
                StepBlock(
                    description=current_description,
                    lines=current_lines,
                    original_index=step_index - 1 if current_description else None,
                )
            )
        return blocks

    @staticmethod
    def _active_positions(blocks: list[StepBlock]) -> list[int]:
        positions: list[int] = []
        for index, block in enumerate(blocks):
            if block.lines and "reason=\"Removed from spec\"" in block.lines[0]:
                continue
            positions.append(index)
        return positions

    @staticmethod
    def _flatten_step_blocks(blocks: list[StepBlock]) -> list[str]:
        flattened: list[str] = []
        for block in blocks:
            flattened.extend(block.lines)
        return flattened
