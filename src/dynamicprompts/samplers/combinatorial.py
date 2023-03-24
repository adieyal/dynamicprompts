from __future__ import annotations

import logging
import typing
from typing import cast

from dynamicprompts.commands import (
    Command,
    LiteralCommand,
    SamplingMethod,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.samplers.base import Sampler
from dynamicprompts.samplers.command_collection import CommandCollection
from dynamicprompts.samplers.utils import wildcard_to_variant
from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.types import StringGen

logger = logging.getLogger(__name__)


def _dedupe(arr: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for item in arr:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return tuple(result)


def _combo_to_prompt(
    sampling_context: SamplingContext,
    combo: list[Command],
) -> typing.Iterable[list[str]]:
    if len(combo) == 0:
        yield []
        return

    c_1, c_rest = combo[0], combo[1:]
    gen = sampling_context.generator_from_command(c_1)
    if sampling_context.get_effective_sampling_method(c_1).is_nonfinite():
        for rest_prompt in _combo_to_prompt(sampling_context, c_rest):
            val = next(gen)
            yield [val] + rest_prompt
    else:
        for p in gen:
            for rest_prompt in _combo_to_prompt(sampling_context, c_rest):
                if rest_prompt:
                    yield [p] + rest_prompt
                else:
                    yield [p]


class CombinatorialSampler(Sampler):
    def _get_sequence(
        self,
        command: SequenceCommand,
        context: SamplingContext,
    ) -> StringGen:
        non_combo_commands = [
            c
            for c in command.tokens
            if c.sampling_method != SamplingMethod.COMBINATORIAL
        ]
        command_collection = CommandCollection(
            non_combo_commands,
            context=context,
        )
        augmented_tokens = [
            LiteralCommand(
                "",
                sampling_method=SamplingMethod.COMBINATORIAL,
            ),  # sentinel 1
            *command.tokens,
            LiteralCommand(
                "",
                sampling_method=SamplingMethod.COMBINATORIAL,
            ),  # sentinel 2
        ]

        def get_sequence(commands: list[Command]) -> typing.Iterable[list[str]]:
            if len(commands) == 0:
                yield []
            else:
                first_command, rest = commands[0], commands[1:]
                if context.get_effective_sampling_method(first_command).is_nonfinite():
                    for rest_vals in get_sequence(rest):
                        val = command_collection.get_value(first_command)
                        if val:
                            yield [val] + rest_vals
                        else:
                            yield rest_vals
                else:
                    gen = context.generator_from_command(first_command)
                    for first_val in gen:
                        for rest_vals in get_sequence(rest):
                            yield [first_val] + rest_vals

        word_arrays = get_sequence(augmented_tokens)
        for word_arr in word_arrays:
            prompt = command.separator.join(word_arr)
            yield prompt.strip(command.separator)

    def _get_variant(
        self,
        variant_command: VariantCommand,
        context: SamplingContext,
    ) -> StringGen:
        if len(variant_command.variants) == 0:
            return

        seen = set()
        is_wildcard_variant = len(variant_command.values) == 1 and isinstance(
            variant_command.values[0],
            WildcardCommand,
        )

        if is_wildcard_variant:
            wildcard_command = cast(WildcardCommand, variant_command.values[0])
            wildcard_variant = wildcard_to_variant(
                wildcard_command,
                context=context,
                min_bound=variant_command.min_bound,
                max_bound=variant_command.max_bound,
                separator=variant_command.separator,
            )
            yield from self._get_variant(wildcard_variant, context)
        else:
            min_bound = min(variant_command.min_bound, len(variant_command.values))
            max_bound = min(variant_command.max_bound, len(variant_command.values))
            for bound in range(
                min_bound,
                max_bound + 1,
            ):
                for combo in variant_command.get_value_combinations(bound):
                    for prompt_arr in _combo_to_prompt(context, combo):
                        deduped_arr = _dedupe(prompt_arr)
                        correct_size = len(deduped_arr) == bound
                        if correct_size and deduped_arr not in seen:
                            seen.add(deduped_arr)
                            yield variant_command.separator.join(deduped_arr)

    def _get_wildcard(
        self,
        command: WildcardCommand,
        context: SamplingContext,
    ) -> StringGen:
        values = context.wildcard_manager.get_all_values(command.wildcard)
        if len(values) == 0:
            logger.warning(f"No values found for wildcard {command.wildcard}")

        for val in values:
            # Parse and generate prompts from wildcard value
            yield from context.sample_prompts(val)

    def _get_literal(
        self,
        command: LiteralCommand,
        context: SamplingContext,
    ) -> StringGen:
        yield command.literal
