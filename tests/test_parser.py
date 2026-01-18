"""Tests for specleft.parser module."""

from __future__ import annotations

from pathlib import Path

import pytest
from specleft.parser import SpecParser
from specleft.schema import ExecutionTime, Priority, StepType
from specleft.validator import collect_spec_stats, load_specs_directory


def _write_file(path: Path, content: str) -> None:
    path.write_text(content)


def test_parse_directory_missing(tmp_path: Path) -> None:
    parser = SpecParser()

    missing = tmp_path / "features"
    with pytest.raises(FileNotFoundError):
        parser.parse_directory(missing)


def test_parse_minimal_tree(tmp_path: Path) -> None:
    parser = SpecParser()

    feature_dir = tmp_path / "calculator"
    story_dir = feature_dir / "addition"
    story_dir.mkdir(parents=True)

    _write_file(
        story_dir / "basic_addition.md",
        """
---
scenario_id: basic-addition
priority: critical
tags: [smoke]
execution_time: fast
---

# Scenario: Basic addition

Adds two numbers together.

## Steps
- **Given** calculator is initialized
- **When** adding `2` and `3`
- **Then** result should be `5`
""".strip(),
    )

    config = parser.parse_directory(tmp_path)

    assert len(config.features) == 1
    feature = config.features[0]
    assert feature.feature_id == "calculator"
    assert feature.name == "Calculator"
    assert feature.stories[0].story_id == "addition"

    scenario = feature.stories[0].scenarios[0]
    assert scenario.scenario_id == "basic-addition"
    assert scenario.priority == Priority.CRITICAL
    assert scenario.execution_time == ExecutionTime.FAST
    assert scenario.steps[0].type == StepType.GIVEN
    assert scenario.steps[1].description == "adding 2 and 3"


def test_parse_feature_story_files(tmp_path: Path) -> None:
    parser = SpecParser()

    feature_dir = tmp_path / "string_utils"
    story_dir = feature_dir / "uppercase"
    story_dir.mkdir(parents=True)

    _write_file(
        feature_dir / "_feature.md",
        """
---
feature_id: string-utils
component: text
owner: core-team
priority: high
tags: [core]
---

# Feature: String Utilities

Feature description text.
""".strip(),
    )

    _write_file(
        story_dir / "_story.md",
        """
---
story_id: uppercase
priority: medium
tags: [smoke, text]
---

# Story: Uppercase conversion

Converts input to uppercase.
""".strip(),
    )

    _write_file(
        story_dir / "convert_to_uppercase.md",
        """
---
scenario_id: convert-to-uppercase
priority: low
tags: [text]
execution_time: medium
---

# Scenario: Convert to uppercase

## Steps
- **Given** input is `hello`
- **When** converting to uppercase
- **Then** result is `HELLO`
""".strip(),
    )

    config = parser.parse_directory(tmp_path)
    feature = config.features[0]
    story = feature.stories[0]
    scenario = story.scenarios[0]

    assert feature.feature_id == "string-utils"
    assert feature.component == "text"
    assert feature.owner == "core-team"
    assert feature.priority == Priority.HIGH
    assert feature.tags == ["core"]

    assert story.story_id == "uppercase"
    assert story.priority == Priority.MEDIUM
    assert story.tags == ["smoke", "text"]

    assert scenario.execution_time == ExecutionTime.MEDIUM


def test_parse_test_data_table(tmp_path: Path) -> None:
    parser = SpecParser()

    feature_dir = tmp_path / "calculator"
    story_dir = feature_dir / "addition"
    story_dir.mkdir(parents=True)

    _write_file(
        story_dir / "basic_addition.md",
        """
---
scenario_id: basic-addition
priority: critical
---

# Scenario: Basic addition

## Test Data
| a | b | expected | description |
|---|---|----------|-------------|
| 2 | 3 | 5 | Small numbers |
| 10 | 15 | 25 | Medium numbers |

## Steps
- **When** adding `{a}` and `{b}`
- **Then** result should be `{expected}`
""".strip(),
    )

    config = parser.parse_directory(tmp_path)
    scenario = config.features[0].stories[0].scenarios[0]

    assert scenario.is_parameterized is True
    assert scenario.test_data[0].params["a"] == 2
    assert scenario.test_data[0].params["b"] == 3
    assert scenario.test_data[1].description == "Medium numbers"


def test_parse_description_block(tmp_path: Path) -> None:
    parser = SpecParser()

    feature_dir = tmp_path / "calculator"
    story_dir = feature_dir / "addition"
    story_dir.mkdir(parents=True)

    _write_file(
        story_dir / "basic_addition.md",
        """
---
scenario_id: basic-addition
---

# Scenario: Basic addition

This scenario adds two numbers.
It should support multiple lines.

## Steps
- **Given** calculator is ready
""".strip(),
    )

    config = parser.parse_directory(tmp_path)
    scenario = config.features[0].stories[0].scenarios[0]

    assert (
        scenario.description
        == "This scenario adds two numbers. It should support multiple lines."
    )


def test_load_specs_directory_and_stats(tmp_path: Path) -> None:
    feature_dir = tmp_path / "calculator"
    story_dir = feature_dir / "addition"
    story_dir.mkdir(parents=True)

    _write_file(
        feature_dir / "_feature.md",
        """
---
feature_id: calculator
priority: high
---

# Feature: Calculator
""".strip(),
    )

    _write_file(
        story_dir / "_story.md",
        """
---
story_id: addition
priority: low
tags: [math]
---

# Story: Addition
""".strip(),
    )

    _write_file(
        story_dir / "basic_addition.md",
        """
---
scenario_id: basic-addition
priority: critical
tags: [smoke]
---

# Scenario: Basic addition

## Steps
- **Given** calculator is ready
- **When** adding numbers
- **Then** result is shown
""".strip(),
    )

    config = load_specs_directory(tmp_path)
    stats = collect_spec_stats(config)

    assert stats.feature_count == 1
    assert stats.story_count == 1
    assert stats.scenario_count == 1
    assert stats.step_count == 3
    assert stats.tags == {"math", "smoke"}
