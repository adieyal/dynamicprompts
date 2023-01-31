from __future__ import annotations

from enum import Enum, auto


class Command:
    """Base class for commands."""


class SamplingMethod(Enum):
    RANDOM = auto()
    COMBINATORIAL = auto()
    DEFAULT = auto()
