from __future__ import annotations

import logging
import typing
from random import Random

from dynamicprompts.commands import (
    Command,
    LiteralCommand,
    SamplingMethod,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.samplers.base import Sampler
from dynamicprompts.wildcardmanager import WildcardManager

logger = logging.getLogger(__name__)

DEFAULT_RANDOM = Random()


def _get_random_variant(
    sampler: Sampler,
    variant_command: VariantCommand,
    random: Random,
) -> typing.Generator[str, None, None]:
    from dynamicprompts.samplers.combinatorial import CombinatorialSampler

    if variant_command.sampling_method == SamplingMethod.COMBINATORIAL:
        new_sampler = CombinatorialSampler(wildcard_manager=sampler._wildcard_manager)
        while True:
            yield from new_sampler.generate_prompts(variant_command)
    else:
        if len(variant_command.values) == 0:
            return
        elif len(variant_command.values) == 1:
            yield from sampler.generator_from_command(variant_command.values[0])
        else:
            while True:
                num_choices = random.randint(
                    variant_command.min_bound,
                    variant_command.max_bound,
                )
                selected_commands = random.choices(
                    variant_command.values,
                    weights=variant_command.weights,
                    k=num_choices,
                )
                sub_generators = [
                    sampler.generator_from_command(c) for c in selected_commands
                ]
                yield variant_command.separator.join(
                    next(subgen) for subgen in sub_generators
                )


def _get_random_wildcard(
    sampler: RandomSampler,
    command: WildcardCommand,
    random: Random,
) -> typing.Generator[str, None, None]:
    from dynamicprompts.samplers.combinatorial import CombinatorialSampler

    if command.sampling_method == SamplingMethod.COMBINATORIAL:
        while True:
            yield from CombinatorialSampler(
                wildcard_manager=sampler._wildcard_manager,
            ).generate_prompts(command)
    else:
        values = sampler._wildcard_manager.get_all_values(command.wildcard)
        while True:
            if len(values) == 0:
                logger.warning(f"No values found for wildcard {command.wildcard}")
                yield f"__{command.wildcard}__"
            else:
                value = sampler._random.choice(values)
                # Parse and generate prompts from wildcard value
                yield from sampler.generate_prompts(value, 1)


class RandomSampler(Sampler):
    def __init__(
        self,
        *,
        wildcard_manager: WildcardManager,
        ignore_whitespace: bool = False,
        rand: Random = DEFAULT_RANDOM,
    ):
        super().__init__(
            wildcard_manager=wildcard_manager,
            ignore_whitespace=ignore_whitespace,
        )
        self._random = rand

    def generator_from_command(
        self,
        command: Command,
    ) -> typing.Generator[str, None, None]:
        if isinstance(command, LiteralCommand):
            while True:
                yield command.literal
        elif isinstance(command, SequenceCommand):
            sub_generators = [self.generator_from_command(c) for c in command.tokens]
            while True:
                yield command.separator.join(next(subgen) for subgen in sub_generators)
        elif isinstance(command, VariantCommand):
            yield from _get_random_variant(self, command, self._random)
        elif isinstance(command, WildcardCommand):
            yield from _get_random_wildcard(self, command, self._random)
        else:
            raise NotImplementedError(
                f"{self.__class__.__qualname__}: Not implemented: {command}",
            )
