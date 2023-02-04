from __future__ import annotations

from itertools import cycle
from typing import Generator, Iterable

from dynamicprompts.commands import (
    Command,
    LiteralCommand,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.samplers.base import Sampler, SamplerManager
from dynamicprompts.wildcardmanager import WildcardManager


def rotate_all(generators: list[Generator[str, None, None]]) -> list[str]:
    return [next(gen) for gen in generators]


def rotate_and_join(
    generators: list[Generator[str, None, None]],
    *,
    separator: str,
) -> str:
    return separator.join(rotate_all(generators))


def next_sampler_next_value(
    samplers: Iterable[Generator[str, None, None]],
) -> Generator[str, None, None]:
    yield from (next(iter(sampler)) for sampler in cycle(samplers))


def _get_combination_samples(
    combo: list[Command],
    sampler_manager: SamplerManager,
) -> Generator[list[str], None, None]:

    if len(combo) == 0:
        while True:
            yield []
    else:
        c_1, c_rest = combo[0], combo[1:]

        gen = sampler_manager.generator_from_command(c_1)
        rest_gen = _get_combination_samples(c_rest, sampler_manager)
        arrs = ([next(gen)] + r for r in rest_gen)

        yield from arrs


class CyclicalSampler(Sampler):
    def __init__(
        self,
        *,
        wildcard_manager: WildcardManager,
        ignore_whitespace: bool = False,
        sampler_manager: SamplerManager,
    ):
        super().__init__(
            wildcard_manager=wildcard_manager,
            ignore_whitespace=ignore_whitespace,
        )
        self._sampler_manager = sampler_manager
        self._already_looping = False

    def _get_cyclical_sequence(
        self,
        tokens: list[Command],
        *,
        separator: str,
    ) -> Generator[str, None, None]:

        generators = [
            self._sampler_manager.generator_from_command(token) for token in tokens
        ]

        while True:
            yield rotate_and_join(generators, separator="")

    def _get_cyclical_variant(
        self,
        variant_command: VariantCommand,
    ) -> Generator[str, None, None]:

        combinations = (
            combo
            for bound in range(variant_command.min_bound, variant_command.max_bound + 1)
            for combo in variant_command.get_value_combinations(bound)
        )

        combination_samplers = cycle(
            (
                variant_command.separator.join(sample)
                for sample in _get_combination_samples(combo, self._sampler_manager)
            )
            for combo in combinations
        )

        while True:
            yield from next_sampler_next_value(combination_samplers)

    def _get_cyclical_wildcard(self, command: WildcardCommand):
        values = self._wildcard_manager.get_all_values(command.wildcard)
        value_samplers = (self._sampler_manager.sample_prompts(val) for val in values)

        while True:
            yield from next_sampler_next_value(value_samplers)

    def _get_cyclical_literal(self, command: LiteralCommand):
        while True:
            yield command.literal

    def generator_from_command(
        self,
        command: Command,
    ) -> Generator[str, None, None]:

        if isinstance(command, LiteralCommand):
            yield from self._get_cyclical_literal(command)
        elif isinstance(command, SequenceCommand):
            yield from self._get_cyclical_sequence(
                command.tokens,
                separator=command.separator,
            )
        elif isinstance(command, VariantCommand):
            yield from self._get_cyclical_variant(command)
        elif isinstance(command, WildcardCommand):
            yield from self._get_cyclical_wildcard(command)
        else:
            raise NotImplementedError(
                f"{self.__class__.__name__} does not support {command.__class__.__name__}",
            )
