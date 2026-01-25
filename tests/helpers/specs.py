"""Spec file creation helpers for tests."""

from __future__ import annotations

from pathlib import Path

from tests.helpers.filesystem import write_file


def create_feature_specs(
    base_dir: Path,
    *,
    feature_id: str,
    story_id: str,
    scenario_id: str,
    include_test_data: bool = False,
    features_dir_name: str = "features",
    scenario_priority: str = "high",
    execution_time: str = "fast",
) -> Path:
    """Create a nested feature spec structure for testing.

    Creates:
        features/<feature_id>/_feature.md
        features/<feature_id>/<story_id>/_story.md
        features/<feature_id>/<story_id>/<scenario_id>.md

    Args:
        base_dir: Base directory to create features in.
        feature_id: The feature ID.
        story_id: The story ID.
        scenario_id: The scenario ID.
        include_test_data: Whether to include test data table.
        features_dir_name: Name of features directory (default: "features").
        scenario_priority: Priority level for the scenario.
        execution_time: Execution time for the scenario.

    Returns:
        Path to the features directory.
    """
    features_dir = base_dir / features_dir_name
    feature_dir = features_dir / feature_id
    story_dir = feature_dir / story_id
    story_dir.mkdir(parents=True, exist_ok=True)

    scenario_file = story_dir / f"{scenario_id.replace('-', '_')}.md"

    write_file(
        feature_dir / "_feature.md",
        f"""
        ---
        feature_id: {feature_id}
        priority: high
        tags: [core]
        ---

        # Feature: {feature_id.title()} Feature
        """,
    )

    write_file(
        story_dir / "_story.md",
        f"""
        ---
        story_id: {story_id}
        tags: [smoke]
        ---

        # Story: {story_id.title()} Story
        """,
    )

    test_data_block = ""
    if include_test_data:
        test_data_block = """
        ## Test Data
        | input | expected | description |
        |-------|----------|-------------|
        | a | A | lowercase a |
        | b | B | lowercase b |
        """

    write_file(
        scenario_file,
        f"""
        ---
        scenario_id: {scenario_id}
        priority: {scenario_priority}
        tags: [smoke]
        execution_time: {execution_time}
        ---

        # Scenario: {scenario_id.replace('-', ' ').title()}

        {test_data_block}
        ## Steps
        - **Given** a user exists
        - **When** the user logs in
        - **Then** access is granted
        """,
    )

    return features_dir


def create_single_file_feature_spec(
    base_dir: Path,
    *,
    feature_id: str,
    scenario_id: str,
    features_dir_name: str = "features",
    scenario_priority: str = "high",
) -> Path:
    """Create a single-file feature spec for testing.

    Creates:
        features/<feature_id>.md

    Args:
        base_dir: Base directory to create features in.
        feature_id: The feature ID.
        scenario_id: The scenario ID.
        features_dir_name: Name of features directory (default: "features").
        scenario_priority: Priority level for the scenario.

    Returns:
        Path to the features directory.
    """
    features_dir = base_dir / features_dir_name
    features_dir.mkdir(parents=True, exist_ok=True)

    write_file(
        features_dir / f"{feature_id}.md",
        f"""
        # Feature: {feature_id.title()} Feature

        ## Scenarios

        ### Scenario: {scenario_id.replace('-', ' ').title()}
        priority: {scenario_priority}

        - Given a user exists
        - When the user logs in
        - Then access is granted
        """,
    )

    return features_dir


def write_specs_tree(base_dir: Path) -> Path:
    """Create a full Markdown specs tree for plugin tests.

    Creates a nested structure with multiple features, stories, and scenarios.

    Args:
        base_dir: Base directory to create specs in.

    Returns:
        Path to the features directory.
    """
    features_dir = base_dir / "features"
    auth_story_dir = features_dir / "auth" / "login"
    parse_story_dir = features_dir / "parse" / "units"
    auth_story_dir.mkdir(parents=True, exist_ok=True)
    parse_story_dir.mkdir(parents=True, exist_ok=True)

    (features_dir / "auth" / "_feature.md").write_text(
        """
---
feature_id: auth
priority: critical
tags: [core]
---

# Feature: User Authentication
""".strip()
    )
    (auth_story_dir / "_story.md").write_text(
        """
---
story_id: login
priority: high
tags: [auth-flow]
---

# Story: Login
""".strip()
    )
    (auth_story_dir / "login_success.md").write_text(
        """
---
scenario_id: login-success
priority: high
tags: [smoke, critical, auth-flow]
execution_time: fast
---

# Scenario: Successful login

## Steps
- **Given** user has valid credentials
- **When** user logs in
- **Then** user sees dashboard
""".strip()
    )
    (auth_story_dir / "login_failure.md").write_text(
        """
---
scenario_id: login-failure
priority: medium
tags: [regression, negative]
execution_time: fast
---

# Scenario: Failed login

## Steps
- **Given** user has invalid credentials
- **When** user tries to log in
- **Then** user sees error message
""".strip()
    )

    (features_dir / "parse" / "_feature.md").write_text(
        """
---
feature_id: parse
priority: high
tags: [unit]
---

# Feature: Unit Parsing
""".strip()
    )
    (parse_story_dir / "_story.md").write_text(
        """
---
story_id: units
priority: medium
tags: [parsing]
---

# Story: Units
""".strip()
    )
    (parse_story_dir / "extract_unit.md").write_text(
        """
---
scenario_id: extract-unit
priority: medium
tags: [unit, parsing]
execution_time: fast
---

# Scenario: Extract unit from string

## Steps
- **When** extracting unit
- **Then** unit is correct
""".strip()
    )

    return features_dir
