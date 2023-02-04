from __future__ import annotations

from enum import Enum


class SamplingMethod(Enum):
    RANDOM = "random"
    COMBINATORIAL = "combinatorial"
    CYCLICAL = "cycle"
    DEFAULT = "default"


class Command:
    """Base class for commands."""

    sampling_method: SamplingMethod = SamplingMethod.DEFAULT
