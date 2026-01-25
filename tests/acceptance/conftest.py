"""Shared pytest fixtures for acceptance tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.fixture
def acceptance_workspace() -> Iterator[tuple[CliRunner, Path]]:
    """Provide an isolated workspace with a default features directory."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        workspace = Path.cwd()
        (workspace / "features").mkdir(exist_ok=True)
        yield runner, workspace
