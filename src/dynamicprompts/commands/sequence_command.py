from __future__ import annotations

import dataclasses
from typing import Iterable

from dynamicprompts.commands import Command, LiteralCommand, SamplingMethod


@dataclasses.dataclass
class SequenceCommand(Command):
    tokens: list[Command]
    separator: str = ""
    sampling_method: SamplingMethod = SamplingMethod.DEFAULT

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

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, SequenceCommand):
            return (
                self.tokens == __o.tokens
                and self.separator == __o.separator
                and self.sampling_method == __o.sampling_method
            )
        return False

    def propagate_sampling_method(
        self,
        sampling_method: SamplingMethod,
    ) -> None:
        super().propagate_sampling_method(sampling_method=sampling_method)

        for token in self.tokens:
            token.propagate_sampling_method(self.sampling_method)

    @classmethod
    def from_literals(
        cls,
        values: list[str | Command],
        *,
        separator: str = "",
        sampling_method: SamplingMethod = SamplingMethod.DEFAULT,
    ) -> SequenceCommand:
        return SequenceCommand(
            tokens=[
                v
                if isinstance(v, Command)
                else LiteralCommand(str(v), sampling_method=sampling_method)
                for v in values
            ],
            separator=separator,
            sampling_method=sampling_method,
        )
