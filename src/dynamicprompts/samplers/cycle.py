from __future__ import annotations

import logging
from itertools import cycle
from typing import Generator, Iterable

from dynamicprompts.commands import (
    Command,
    LiteralCommand,
    SamplingMethod,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.samplers.base import Sampler, SamplerRouter
from dynamicprompts.types import StringGen
from dynamicprompts.utils import next_sampler_next_value
from dynamicprompts.wildcardmanager import WildcardManager

logger = logging.getLogger(__name__)


def _get_combination_samples(
    combo: list[Command],
    sampler_manager: SamplerRouter,
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
        sampler_manager: SamplerRouter,
    ):
        super().__init__(
            wildcard_manager=wildcard_manager,
            ignore_whitespace=ignore_whitespace,
            sampler_manager=sampler_manager,
        )
        self._already_looping = False

    def _propograte_sampling_method(self, commands: Iterable[Command]) -> None:
        for cmd in commands:
            if cmd.sampling_method == SamplingMethod.DEFAULT:
                cmd.sampling_method = SamplingMethod.CYCLICAL

    def _get_cyclical_variant(
        self,
        variant_command: VariantCommand,
    ) -> StringGen:

        if len(variant_command.values) == 0:
            return

        self._propograte_sampling_method(variant_command.values)

        combinations = (
            combo
            for bound in range(variant_command.min_bound, variant_command.max_bound + 1)
            for combo in variant_command.get_value_combinations(bound)
        )

        combination_samplers = (
            (
                variant_command.separator.join(sample)
                for sample in _get_combination_samples(combo, self._sampler_manager)
            )
            for combo in combinations
        )

        while True:
            yield from next_sampler_next_value(cycle(combination_samplers))

    def _get_cyclical_wildcard(self, command: WildcardCommand):
        values = self._wildcard_manager.get_all_values(command.wildcard)
        value_samplers = (self._sampler_manager.sample_prompts(val) for val in values)

        if len(values) == 0:
            logger.warning(f"No values found for wildcard {command.wildcard}")

        while True:
            if len(values) == 0:
                yield f"__{command.wildcard}__"
            else:
                yield from next_sampler_next_value(value_samplers)

    def generator_from_command(
        self,
        command: Command,
    ) -> StringGen:

        if isinstance(command, LiteralCommand):
            yield from self._get_literal(command)
        elif isinstance(command, SequenceCommand):
            yield from self._get_sequence(command)
        elif isinstance(command, VariantCommand):
            yield from self._get_cyclical_variant(command)
        elif isinstance(command, WildcardCommand):
            yield from self._get_cyclical_wildcard(command)
        else:
            raise NotImplementedError(
                f"{self.__class__.__name__} does not support {command.__class__.__name__}",
            )
