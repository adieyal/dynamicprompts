from __future__ import annotations

import dataclasses
import itertools
import random
from functools import cached_property
from typing import Iterable, Iterator

from dynamicprompts.wildcards.item import WildcardItem


@dataclasses.dataclass(frozen=True)
class WildcardValues:
    """
    Collection of wildcard values; has a flag for whether any value may have
    varied weights, and as such requires special weighted sampling too.

    Immutable.
    """

    items: tuple[str | WildcardItem, ...]

    def __iter__(self) -> Iterable[str | WildcardItem]:
        return iter(self.items)

    def __getitem__(self, item) -> str | WildcardItem:
        return self.items[item]

    def __len__(self) -> int:
        return len(self.items)

    def __bool__(self) -> bool:
        return bool(self.items)

    def __add__(self, other: WildcardValues) -> WildcardValues:
        """
        Combine two WildcardValues collections.
        """
        if not isinstance(other, WildcardValues):
            raise TypeError(f"Cannot add WildcardValues and {type(other)}")
        return WildcardValues.from_items(self.items + other.items)

    @cached_property
    def has_varied_weights(self) -> bool:
        """
        Whether the weights of the items in this collection vary.

        Users can use this to avoid a weighted random generator if they know
        that all the weights are the same.
        """
        weights_seen = set()
        for item in self.items:
            weight = getattr(item, "weight", 1)
            weights_seen.add(weight)
            if len(weights_seen) > 1:
                return True
        return False

    @cached_property
    def string_values(self) -> list[str]:
        """
        String values, no weights, of the items in this collection.
        """
        return [str(item) for item in self.items]

    @cached_property
    def cum_weight_values(self) -> list[float]:
        """
        Cumulative weights of the items in this collection.
        """
        weights = [getattr(item, "weight", 1) for item in self.items]
        return list(itertools.accumulate(weights))

    def copy(self) -> WildcardValues:
        return dataclasses.replace(self, items=tuple(self.items))

    def shuffled(self, rng=random) -> WildcardValues:
        """
        Return a shuffled copy of this collection.
        """
        items = list(self.items)
        rng.shuffle(items)
        return dataclasses.replace(self, items=tuple(items))

    @classmethod
    def from_items(cls, wildcards: Iterable[str | WildcardItem]) -> WildcardValues:
        """
        Create a WildcardValues collection from an iterable of items (strings or WildcardItems).
        """
        return cls(tuple(wildcards))

    def iterate_string_values_weighted(self) -> Iterator[str]:
        """
        Iterate over the string values, repeating each one according to its weight.

        Decimal weights are truncated down to integers.
        """
        # TODO: right now this does repeat each item according to weight,
        #       e.g. `A A A B B C [...]`, but maybe it should do `A B C A B A [...]` instead?
        for item in self.items:
            weight = getattr(item, "weight", 1)
            for _ in range(int(weight)):
                yield str(item)

    def get_weighted_random_generator(self, rng: random.Random) -> Iterator[str]:
        """
        Get a generator that yields random values from the wildcard collection.

        If any values have weights, they will be picked according to their weight.
        """
        if not self.has_varied_weights:
            # Simple case: just a random choice
            while True:
                yield rng.choice(self.string_values)
        else:
            cum_weights = self.cum_weight_values
            while True:
                # Grab a bunch (but not too many) random values at a time,
                # to reduce the number of calls to `choices`.
                yield from rng.choices(
                    self.string_values,
                    cum_weights=cum_weights,
                    k=10,
                )
