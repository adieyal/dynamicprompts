from __future__ import annotations

import random
from collections import OrderedDict
from itertools import cycle
from typing import Iterable, TypeVar

from dynamicprompts.types import StringGen

T = TypeVar("T")


def removeprefix(s: str, prefix: str) -> str:
    return s[len(prefix) :] if s.startswith(prefix) else s


def removesuffix(s: str, suffix: str) -> str:
    return s[: -len(suffix)] if s.endswith(suffix) else s


def squash_whitespace(s: str) -> str:
    return " ".join(s.split())


def is_empty_line(line: str | None) -> bool:
    return line is None or line.strip() == "" or line.strip().startswith("#")


def dedupe(arr: list[str]) -> tuple[str, ...]:
    ordered_dict = OrderedDict.fromkeys(arr)
    return tuple(ordered_dict.keys())


def rotate_all(generators: Iterable[StringGen]) -> list[str]:
    return [next(gen) for gen in generators]


def rotate_and_join(
    generators: Iterable[StringGen],
    *,
    separator: str,
) -> str:
    return separator.join(rotate_all(generators))


def next_sampler_next_value(
    samplers: Iterable[StringGen],
) -> StringGen:
    yield from (next(iter(sampler)) for sampler in cycle(samplers))


def cross(l1: Iterable[T], l2: Iterable[T]) -> Iterable[tuple[T, T]]:
    for e1 in l1:
        for e2 in l2:
            if e1 != e2:
                yield (e1, e2)


def choose_without_replacement(
    values: list[T],
    *,
    weights: list[float],
    num_choices: int,
    rand=random,
) -> list[T]:
    values = values.copy()
    weights = weights.copy()

    if len(values) < num_choices:
        raise ValueError(
            f"You asked for {num_choices} values, but only {len(values)} are available in {values}.",
        )

    if not weights:
        weights = [1.0 for _ in range(len(values))]

    if len(values) != len(weights):
        raise ValueError(
            f"Number of values ({len(values)}) and weights ({len(weights)}) must be the same.",
        )

    if len(values) == 0:
        return []
    elif len(values) == 1:
        return values
    else:
        chosen_values = []
        for _ in range(num_choices):
            chosen = rand.choices(values, weights=weights, k=1)[0]
            chosen_values.append(chosen)
            weights.remove(weights[values.index(chosen)])
            values.remove(chosen)
        return chosen_values
