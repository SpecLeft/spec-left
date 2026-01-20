"""Filesystem utilities used across CLI commands."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any


@contextmanager
def working_directory(path: Path) -> Any:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def record_file_snapshot(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in root.rglob("*"):
        if path.is_file():
            snapshot[str(path.relative_to(root))] = path.read_text()
    return snapshot


def compare_file_snapshot(root: Path, snapshot: dict[str, str]) -> bool:
    current = record_file_snapshot(root)
    return current == snapshot
