from __future__ import annotations

import dataclasses
import logging
from typing import Iterable

from dynamicprompts.commands import Command, LiteralCommand, SamplingMethod

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class VariantOption:
    value: Command
    weight: float = 1.0


@dataclasses.dataclass
class VariantCommand(Command):
    variants: list[VariantOption]
    min_bound: int = 1
    max_bound: int = 1
    separator: str = ","
    sampling_method: SamplingMethod = SamplingMethod.DEFAULT

    def __post_init__(self):
        min_bound, max_bound = sorted((self.min_bound, self.max_bound))
        self.min_bound = max(0, min_bound)
        self.max_bound = max_bound

    def __len__(self) -> int:
        return len(self.variants)

    def __getitem__(self, index: int) -> VariantOption:
        return self.variants[index]

    def __iter__(self) -> Iterable[VariantOption]:
        return iter(self.variants)

    @property
    def weights(self) -> list[float]:
        return [p.weight for p in self.variants]

    @property
    def values(self) -> list[Command]:
        return [p.value for p in self.variants]

    @classmethod
    def from_literals_and_weights(
        cls,
        literals: list[str],
        weights: list[float] | None = None,
        min_bound: int = 1,
        max_bound: int = 1,
        separator: str = ",",
        sampling_method: SamplingMethod = SamplingMethod.DEFAULT,
    ) -> VariantCommand:
        vals = [LiteralCommand(str(v)) for v in literals]
        if weights is None:
            weights = [1.0] * len(vals)
        assert len(vals) == len(weights), "Must have same number of weights as values"
        return VariantCommand(
            variants=[VariantOption(v, w) for v, w in zip(vals, weights)],
            min_bound=min_bound,
            max_bound=max_bound,
            separator=separator,
            sampling_method=sampling_method,
        )

    def get_value_combinations(self, k: int) -> Iterable[list[Command]]:
        if k <= 0:
            yield []
        else:
            for variant in self.values:
                for item in self.get_value_combinations(k - 1):
                    yield [variant] + item
