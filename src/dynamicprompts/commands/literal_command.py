from __future__ import annotations

import dataclasses

from dynamicprompts.commands import Command


@dataclasses.dataclass
class LiteralCommand(Command):
    literal: str

    def __add__(self, other):
        if isinstance(other, LiteralCommand):
            return LiteralCommand(f"{self.literal} {other.literal}")
        raise TypeError(f"Cannot concatenate LiteralCommand with {other}")
