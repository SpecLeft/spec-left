"""Text helpers that are reusable outside the CLI."""

from __future__ import annotations

import re


def to_snake_case(name: str) -> str:
    """Convert a string to snake_case."""
    s = re.sub(r"[-\s]+", "_", name)
    s = re.sub(r"([A-Z])", r"_\1", s).lower()
    return re.sub(r"_+", "_", s).strip("_")
