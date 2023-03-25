from __future__ import annotations

import logging
from random import Random

from dynamicprompts.commands import (
    Command,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.samplers.base import Sampler
from dynamicprompts.samplers.utils import wildcard_to_variant
from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.types import StringGen
from dynamicprompts.utils import choose_without_replacement, rotate_and_join

logger = logging.getLogger(__name__)


class RandomSampler(Sampler):
    def _get_variant_choices(
        self,
        values: list[Command],
        weights: list[float],
        num_choices: int,
        rand: Random,
    ) -> list[Command]:
        # Wraps choose_without_replacement for ease of testing

        return choose_without_replacement(
            values,
            weights=weights,
            num_choices=num_choices,
            rand=rand,
        )

    def _get_variant_num_choices(
        self,
        command: VariantCommand,
        context: SamplingContext,
    ) -> int:
        # Wraps randint for ease of testing
        return context.rand.randint(
            command.min_bound,
            command.max_bound,
        )

    def _get_wildcard_choice(self, context: SamplingContext, values: list[str]) -> str:
        # Wraps choice for ease of testing
        return context.rand.choice(values)

    def _get_variant(
        self,
        command: VariantCommand,
        context: SamplingContext,
    ) -> StringGen:
        if len(command.values) == 0:
            return
        elif len(command.values) == 1:
            if isinstance(command.values[0], WildcardCommand):
                wildcard_variant = wildcard_to_variant(
                    command.values[0],
                    context=context,
                    min_bound=command.min_bound,
                    max_bound=command.max_bound,
                    separator=command.separator,
                )

                yield from self._get_variant(wildcard_variant, context)
            else:
                yield from context.generator_from_command(
                    command.values[0],
                )
            return
        while True:
            command = command.adjust_range()

            num_choices = min(
                command.max_bound,
                self._get_variant_num_choices(command, context),
            )

            selected_commands = self._get_variant_choices(
                command.values,
                weights=command.weights,
                num_choices=num_choices,
                rand=context.rand,
            )
            sub_generators = [
                context.generator_from_command(c) for c in selected_commands
            ]

            if len(sub_generators) == 0:
                yield ""
            else:
                yield rotate_and_join(
                    sub_generators,
                    separator=command.separator,
                )

    def _get_wildcard(
        self,
        command: WildcardCommand,
        context: SamplingContext,
    ) -> StringGen:
        values = context.wildcard_manager.get_all_values(command.wildcard)

        if len(values) == 0:
            logger.warning(f"No values found for wildcard {command.wildcard}")

        while True:
            if len(values) == 0:
                yield context.wildcard_manager.to_wildcard(command.wildcard)
            else:
                value = self._get_wildcard_choice(context, values)
                yield from context.sample_prompts(value, 1)
