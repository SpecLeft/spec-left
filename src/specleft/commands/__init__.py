"""Command group modules for the SpecLeft CLI."""

from __future__ import annotations

from specleft.commands.contract import contract
from specleft.commands.coverage import coverage
from specleft.commands.doctor import doctor
from specleft.commands.features import features
from specleft.commands.init import init
from specleft.commands.next import next_command
from specleft.commands.status import status
from specleft.commands.test import test


__all__ = [
    "contract",
    "coverage",
    "doctor",
    "features",
    "init",
    "next_command",
    "status",
    "test",
]
