from __future__ import annotations

import dataclasses

from dynamicprompts.commands.base import Command
from dynamicprompts.enums import SamplingMethod


@dataclasses.dataclass(frozen=True)
class WildcardCommand(Command):
    wildcard: Command | str
    sampling_method: SamplingMethod | None = None
    variables: dict[str, Command] = dataclasses.field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.wildcard, (Command, str)):
            raise TypeError(
                f"Wildcard must be a Command or str, not {type(self.wildcard)}",
            )
