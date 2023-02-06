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


def get_arrs(gen: StringGen, rest_gen: Iterable[list[str]]):
    try:
        for r in rest_gen:
            yield [next(gen)] + r
    except StopIteration:
        yield []


def _get_combination_samples(
    combo: list[Command],
    sampler_router: SamplerRouter,
) -> Generator[list[str], None, None]:

    try:
        if len(combo) == 0:
            while True:
                yield []
        else:
            c_1, c_rest = combo[0], combo[1:]

            gen = sampler_router.generator_from_command(c_1)
            rest_gen = _get_combination_samples(c_rest, sampler_router)
            arrs = get_arrs(gen, rest_gen)

            yield from arrs
    except StopIteration:
        return


class CyclicalSampler(Sampler):
    def __init__(
        self,
        *,
        wildcard_manager: WildcardManager,
        ignore_whitespace: bool = False,
        sampler_router: SamplerRouter,
    ):
        super().__init__(
            wildcard_manager=wildcard_manager,
            ignore_whitespace=ignore_whitespace,
            sampler_router=sampler_router,
        )
        self._already_looping = False

    def _propagate_sampling_method(self, commands: Iterable[Command]) -> None:
        for cmd in commands:
            if (
                cmd.sampling_method == SamplingMethod.DEFAULT
                or not cmd.sampling_method.is_nonfinite()
            ):
                cmd.sampling_method = SamplingMethod.CYCLICAL

    def _get_cyclical_variant(
        self,
        variant_command: VariantCommand,
    ) -> StringGen:

        self._propagate_sampling_method(variant_command.values)

        if len(variant_command.values) == 0:
            return

        combinations = (
            combo
            for bound in range(variant_command.min_bound, variant_command.max_bound + 1)
            for combo in variant_command.get_value_combinations(bound)
        )

        combination_samplers = (
            (
                variant_command.separator.join(sample)
                for sample in _get_combination_samples(combo, self._sampler_router)
            )
            for combo in combinations
        )

        while True:
            yield from next_sampler_next_value(cycle(combination_samplers))

    def _get_cyclical_wildcard(self, command: WildcardCommand):
        values = self._wildcard_manager.get_all_values(command.wildcard)
        new_router = self._sampler_router.clone()
        new_router.default_sampling_method = SamplingMethod.CYCLICAL
        value_samplers = [new_router.sample_prompts(val) for val in values]

        if len(values) == 0:
            logger.warning(f"No values found for wildcard {command.wildcard}")
            while True:
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
