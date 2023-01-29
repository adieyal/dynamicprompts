from __future__ import annotations

import dataclasses
from typing import Iterable

from dynamicprompts.commands import (
    Command,
    LiteralCommand,
)


@dataclasses.dataclass
class SequenceCommand(Command):
    tokens: list[Command]
    separator: str = ""

    def __len__(self) -> int:
        return len(self.tokens)

    def __getitem__(self, index: int) -> Command:
        return self.tokens[index]

    def __iter__(self) -> Iterable[Command]:
        return iter(self.tokens)

    def __post_init__(self):
        assert all(
            isinstance(t, Command) for t in self.tokens
        ), "All tokens must be Command instances"

    @classmethod
    def from_literals(
        cls,
        values: list[str | Command],
        *,
        separator: str = "",
    ) -> SequenceCommand:
        return SequenceCommand(
            tokens=[
                v if isinstance(v, Command) else LiteralCommand(str(v)) for v in values
            ],
            separator=separator,
        )
