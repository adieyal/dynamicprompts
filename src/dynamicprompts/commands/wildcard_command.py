from __future__ import annotations

import dataclasses

from dynamicprompts.commands.base import Command
from dynamicprompts.enums import SamplingMethod


@dataclasses.dataclass(frozen=True)
class WildcardCommand(Command):
    wildcard: str
    sampling_method: SamplingMethod | None = None

    def __post_init__(self):
        if not isinstance(self.wildcard, str):
            raise TypeError(f"Wildcard must be a string, not {type(self.wildcard)}")
