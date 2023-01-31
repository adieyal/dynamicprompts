from __future__ import annotations

import dataclasses

from dynamicprompts.commands.base import Command, SamplingMethod


@dataclasses.dataclass
class WildcardCommand(Command):
    wildcard: str
    sampling_method: SamplingMethod = SamplingMethod.DEFAULT

    def __post_init__(self):
        if not isinstance(self.wildcard, str):
            raise TypeError(f"Wildcard must be a string, not {type(self.wildcard)}")
