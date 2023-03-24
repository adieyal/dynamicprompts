from __future__ import annotations

import logging
from itertools import cycle
from typing import Generator, Iterable, cast

from dynamicprompts.commands import (
    Command,
    SamplingMethod,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.samplers.base import Sampler
from dynamicprompts.samplers.utils import wildcard_to_variant
from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.types import StringGen, to_string_gen
from dynamicprompts.utils import next_sampler_next_value

logger = logging.getLogger(__name__)


def get_arrs(gen: StringGen, rest_gen: Iterable[list[str]]):
    try:
        for r in rest_gen:
            yield [next(gen)] + r
    except StopIteration:
        yield []


def _get_combination_samples(
    combo: list[Command],
    sampling_context: SamplingContext,
) -> Generator[list[str], None, None]:
    try:
        if len(combo) == 0:
            while True:
                yield []
        else:
            c_1, c_rest = combo[0], combo[1:]

            gen = sampling_context.generator_from_command(c_1)
            rest_gen = _get_combination_samples(c_rest, sampling_context)
            arrs = get_arrs(gen, rest_gen)

            yield from arrs
    except StopIteration:
        return


class CyclicalSampler(Sampler):
    def _get_variant(
        self,
        command: VariantCommand,
        sampling_context: SamplingContext,
    ) -> StringGen:
        is_wildcard_variant = len(command.values) == 1 and isinstance(
            command.values[0],
            WildcardCommand,
        )

        if len(command.values) == 0:
            return
        elif is_wildcard_variant:
            wildcard_command = cast(WildcardCommand, command.values[0])
            wildcard_variant = wildcard_to_variant(
                wildcard_command,
                context=sampling_context,
                min_bound=command.min_bound,
                max_bound=command.max_bound,
                separator=command.separator,
            )
            yield from self._get_variant(wildcard_variant, sampling_context)
        else:
            min_bound = min(command.min_bound, len(command.values))
            max_bound = min(command.max_bound, len(command.values))

            combinations = (
                combo
                for bound in range(min_bound, max_bound + 1)
                for combo in command.get_value_combinations(bound)
            )

            combination_samplers = (
                (
                    command.separator.join(sample)
                    for sample in _get_combination_samples(combo, sampling_context)
                )
                for combo in combinations
            )

            while True:
                yield from next_sampler_next_value(cycle(combination_samplers))

    def _get_wildcard(
        self,
        command: WildcardCommand,
        sampling_context: SamplingContext,
    ):
        values = sampling_context.wildcard_manager.get_all_values(command.wildcard)
        new_context = sampling_context.with_sampling_method(SamplingMethod.CYCLICAL)
        value_samplers = [new_context.sample_prompts(val) for val in values]
        value_string_gens = [to_string_gen(val) for val in value_samplers]

        if len(values) == 0:
            logger.warning(f"No values found for wildcard {command.wildcard}")
            ww = sampling_context.parser_config.wildcard_wrap
            while True:
                yield f"{ww}{command.wildcard}{ww}"
        else:
            yield from next_sampler_next_value(value_string_gens)
