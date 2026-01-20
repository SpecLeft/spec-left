"""Utility helpers for contract checks."""

from __future__ import annotations

import json
from pathlib import Path


def create_contract_specs(root: Path) -> None:
    _write_text_file(
        root / "features" / "auth" / "_feature.md",
        """
        ---
        feature_id: auth
        priority: high
        ---
        # Feature: Auth
        """,
    )
    _write_text_file(
        root / "features" / "auth" / "login" / "_story.md",
        """
        ---
        story_id: login
        ---
        # Story: Login
        """,
    )
    _write_text_file(
        root / "features" / "auth" / "login" / "login-success.md",
        """
        ---
        scenario_id: login-success
        priority: high
        execution_time: fast
        ---
        # Scenario: Login Success
        ## Steps
        - **Given** a user exists
        - **When** the user logs in
        - **Then** access is granted
        """,
    )


def load_json_output(raw_output: str, *, allow_preamble: bool = False) -> object | None:
    payload = raw_output
    if allow_preamble:
        lines = raw_output.splitlines()
        if lines and lines[0].strip() == "Running contract tests...":
            payload = "\n".join(lines[1:])
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def _write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip())
