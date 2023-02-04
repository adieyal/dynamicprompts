from __future__ import annotations

import logging
from random import Random

from dynamicprompts.commands import (
    Command,
    LiteralCommand,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.samplers.base import Sampler, SamplerManager
from dynamicprompts.types import StringGen
from dynamicprompts.utils import choose_without_replacement, rotate_and_join
from dynamicprompts.wildcardmanager import WildcardManager

logger = logging.getLogger(__name__)

DEFAULT_RANDOM = Random()


class RandomSampler(Sampler):
    def __init__(
        self,
        *,
        wildcard_manager: WildcardManager,
        ignore_whitespace: bool = False,
        sampler_manager: SamplerManager,
        rand: Random = DEFAULT_RANDOM,
    ):
        super().__init__(
            wildcard_manager=wildcard_manager,
            ignore_whitespace=ignore_whitespace,
            sampler_manager=sampler_manager,
        )
        self._sampler_manager = sampler_manager
        self._random = rand

    def _get_choices(
        self,
        values: list[Command],
        weights: list[float],
        num_choices,
    ) -> list[Command]:

        return choose_without_replacement(
            values,
            weights=weights,
            num_choices=num_choices,
            rand=self._random,
        )

    def _get_random_variant(
        self,
        variant_command: VariantCommand,
    ) -> StringGen:

        if len(variant_command.values) == 0:
            return
        elif len(variant_command.values) == 1:
            yield from self._sampler_manager.generator_from_command(
                variant_command.values[0],
            )
        else:
            while True:
                num_choices = self._random.randint(
                    variant_command.min_bound,
                    variant_command.max_bound,
                )

                selected_commands = self._get_choices(
                    variant_command.values,
                    weights=variant_command.weights,
                    num_choices=num_choices,
                )
                sub_generators = [
                    self._sampler_manager.generator_from_command(c)
                    for c in selected_commands
                ]

                if len(sub_generators) == 0:
                    yield ""
                else:
                    yield rotate_and_join(
                        sub_generators,
                        separator=variant_command.separator,
                    )

    def _get_random_wildcard(self, command: WildcardCommand):
        values = self._wildcard_manager.get_all_values(command.wildcard)

        if len(values) == 0:
            logger.warning(f"No values found for wildcard {command.wildcard}")

        while True:
            if len(values) == 0:
                yield f"__{command.wildcard}__"
            else:
                value = self._random.choice(values)
                yield from self._sampler_manager.sample_prompts(value, 1)

    def generator_from_command(self, command: Command) -> StringGen:
        if isinstance(command, LiteralCommand):
            yield from self._get_literal(command)
        elif isinstance(command, SequenceCommand):
            yield from self._get_sequence(command)
        elif isinstance(command, VariantCommand):
            yield from self._get_random_variant(command)
        elif isinstance(command, WildcardCommand):
            yield from self._get_random_wildcard(command)
        else:
            raise NotImplementedError(
                f"{self.__class__.__qualname__}: Not implemented: {command}",
            )
