"""Access helpers to avoid import cycles with CLI entrypoint."""

from __future__ import annotations

from typing import Callable

import click


def get_cli() -> Callable[..., click.Command]:
    from specleft.cli.main import cli

    return cli
