from __future__ import annotations

import dataclasses

from dynamicprompts.commands import Command
from dynamicprompts.enums import SamplingMethod


@dataclasses.dataclass
class LiteralCommand(Command):
    literal: str
    sampling_method: SamplingMethod = SamplingMethod.DEFAULT

    def __add__(self, other):
        if isinstance(other, LiteralCommand):
            return LiteralCommand(f"{self.literal} {other.literal}")
        raise TypeError(f"Cannot concatenate LiteralCommand with {other}")

    def __eq__(self, other):
        if isinstance(other, LiteralCommand):
            return self.literal == other.literal
        return False
