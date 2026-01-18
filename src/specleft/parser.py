"""SpecLeft Markdown Parser.

Parses feature specifications from Markdown files with YAML frontmatter.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import frontmatter

from specleft.schema import (
    ExecutionTime,
    FeatureSpec,
    Priority,
    ScenarioSpec,
    SpecDataRow,
    SpecsConfig,
    SpecStep,
    StepType,
    StorySpec,
)


class SpecParser:
    """Parser for SpecLeft Markdown specifications."""

    FEATURE_FILE = "_feature.md"
    STORY_FILE = "_story.md"

    STEP_PATTERN = re.compile(
        r"^\s*[-*]\s+\*\*(Given|When|Then|And|But)\*\*\s+(.+)$",
        re.IGNORECASE | re.MULTILINE,
    )

    def parse_directory(self, features_dir: Path) -> SpecsConfig:
        """Parse all specifications from a features directory."""
        if not features_dir.exists():
            raise FileNotFoundError(f"Features directory not found: {features_dir}")

        features: list[FeatureSpec] = []

        for feature_dir in sorted(features_dir.iterdir()):
            if feature_dir.is_dir() and not feature_dir.name.startswith("."):
                feature = self._parse_feature_dir(feature_dir)
                if feature:
                    features.append(feature)

        return SpecsConfig(features=features)

    def _parse_feature_dir(self, feature_dir: Path) -> FeatureSpec | None:
        """Parse a feature directory."""
        feature_file = feature_dir / self.FEATURE_FILE

        if feature_file.exists():
            feature = self._parse_feature_file(feature_file)
        else:
            feature = FeatureSpec(
                feature_id=feature_dir.name.lower().replace("_", "-"),
                name=feature_dir.name.replace("_", " ").title(),
            )

        feature.source_dir = feature_dir

        for story_dir in sorted(feature_dir.iterdir()):
            if story_dir.is_dir() and not story_dir.name.startswith("_"):
                story = self._parse_story_dir(story_dir)
                if story:
                    feature.stories.append(story)

        return feature if feature.stories else None

    def _parse_story_dir(self, story_dir: Path) -> StorySpec | None:
        """Parse a story directory."""
        story_file = story_dir / self.STORY_FILE

        if story_file.exists():
            story = self._parse_story_file(story_file)
        else:
            story = StorySpec(
                story_id=story_dir.name.lower().replace("_", "-"),
                name=story_dir.name.replace("_", " ").title(),
            )

        story.source_dir = story_dir

        for scenario_file in sorted(story_dir.glob("*.md")):
            if scenario_file.name.startswith("_"):
                continue
            scenario = self._parse_scenario_file(scenario_file)
            if scenario:
                story.scenarios.append(scenario)

        return story if story.scenarios else None

    def _parse_feature_file(self, filepath: Path) -> FeatureSpec:
        """Parse a _feature.md file."""
        post = frontmatter.load(filepath)
        metadata = post.metadata

        return FeatureSpec(
            feature_id=metadata.get("feature_id", filepath.parent.name),
            name=self._extract_title(post.content) or filepath.parent.name,
            description=self._extract_description(post.content),
            component=metadata.get("component"),
            owner=metadata.get("owner"),
            priority=Priority(metadata.get("priority", "medium")),
            tags=metadata.get("tags", []),
        )

    def _parse_story_file(self, filepath: Path) -> StorySpec:
        """Parse a _story.md file."""
        post = frontmatter.load(filepath)
        metadata = post.metadata

        return StorySpec(
            story_id=metadata.get("story_id", filepath.parent.name),
            name=self._extract_title(post.content) or filepath.parent.name,
            description=self._extract_description(post.content),
            priority=Priority(metadata.get("priority", "medium")),
            tags=metadata.get("tags", []),
        )

    def _parse_scenario_file(self, filepath: Path) -> ScenarioSpec:
        """Parse a scenario.md file."""
        post = frontmatter.load(filepath)
        metadata = post.metadata
        content = post.content

        scenario_id = metadata.get(
            "scenario_id", filepath.stem.lower().replace("_", "-")
        )
        steps = self._parse_steps(content)
        test_data = self._parse_test_data_table(content)

        return ScenarioSpec(
            scenario_id=scenario_id,
            name=self._extract_title(content) or filepath.stem.replace("_", " "),
            description=self._extract_description(content),
            priority=Priority(metadata.get("priority", "medium")),
            tags=metadata.get("tags", []),
            execution_time=ExecutionTime(metadata.get("execution_time", "fast")),
            steps=steps,
            test_data=test_data,
            source_file=filepath,
        )

    def _extract_title(self, content: str) -> str | None:
        """Extract the first H1 title from Markdown content."""
        match = re.search(
            r"^#\s+(?:Scenario:|Story:|Feature:)?\s*(.+)$",
            content,
            re.MULTILINE,
        )
        return match.group(1).strip() if match else None

    def _extract_description(self, content: str) -> str | None:
        """Extract description (first paragraph after title)."""
        lines = content.split("\n")
        in_description = False
        description_lines: list[str] = []

        for line in lines:
            if line.startswith("# "):
                in_description = True
                continue
            if in_description:
                if (
                    line.startswith("#")
                    or line.startswith("## Steps")
                    or line.startswith("## Test Data")
                ):
                    break
                if line.strip():
                    description_lines.append(line.strip())
                elif description_lines:
                    break

        return " ".join(description_lines) if description_lines else None

    def _parse_steps(self, content: str) -> list[SpecStep]:
        """Parse Gherkin steps from Markdown content."""
        steps: list[SpecStep] = []

        steps_match = re.search(r"## Steps\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
        if not steps_match:
            return steps

        for match in self.STEP_PATTERN.finditer(steps_match.group(1)):
            step_type = match.group(1).lower()
            description = match.group(2).strip()
            description = re.sub(r"`([^`]+)`", r"\1", description)

            steps.append(SpecStep(type=StepType(step_type), description=description))

        return steps

    def _parse_test_data_table(self, content: str) -> list[SpecDataRow]:
        """Parse test data table from Markdown content."""
        test_data: list[SpecDataRow] = []

        data_match = re.search(r"## Test Data\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
        if not data_match:
            return test_data

        lines = [
            line.strip() for line in data_match.group(1).split("\n") if line.strip()
        ]
        if len(lines) < 3:
            return test_data

        header_line = lines[0]
        if not header_line.startswith("|"):
            return test_data

        headers = [header.strip() for header in header_line.strip("|").split("|")]

        for line in lines[2:]:
            if not line.startswith("|"):
                continue

            values = [value.strip() for value in line.strip("|").split("|")]
            if len(values) != len(headers):
                continue

            params: dict[str, Any] = {}
            description = None

            for header, value in zip(headers, values, strict=False):
                if header.lower() == "description":
                    description = value
                else:
                    params[header] = self._convert_value(value)

            if params:
                test_data.append(SpecDataRow(params=params, description=description))

        return test_data

    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate Python type."""
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        if value.lower() in ("none", "null", ""):
            return None
        return value
