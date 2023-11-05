from __future__ import annotations

import logging
from typing import Iterable, cast

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
from dynamicprompts.samplers.utils import (
    get_wildcard_not_found_fallback,
    wildcard_to_variant,
)
from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.sampling_result import SamplingResult
from dynamicprompts.types import ResultGen
from dynamicprompts.utils import dedupe

logger = logging.getLogger(__name__)


def _combo_to_prompt(
    sampling_context: SamplingContext,
    combo: list[Command],
) -> Iterable[list[SamplingResult]]:
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
    ) -> ResultGen:
        tokens, context = context.process_variable_assignments(command.tokens)
        non_combo_commands = [
            c for c in tokens if c.sampling_method != SamplingMethod.COMBINATORIAL
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
            *tokens,
            LiteralCommand(
                "",
                sampling_method=SamplingMethod.COMBINATORIAL,
            ),  # sentinel 2
        ]

        def get_sequence(commands: list[Command]) -> Iterable[list[SamplingResult]]:
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

        for result_arr in get_sequence(augmented_tokens):
            yield SamplingResult.joined(result_arr, separator=command.separator)

    def _get_variant(
        self,
        variant_command: VariantCommand,
        context: SamplingContext,
    ) -> ResultGen:
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
            variant_command = variant_command.adjust_range()
            for bound in range(
                variant_command.min_bound,
                variant_command.max_bound + 1,
            ):
                for combo in variant_command.get_value_combinations(bound):
                    for prompt_arr in _combo_to_prompt(context, combo):
                        deduped_arr = dedupe(prompt_arr, key=lambda r: r.dedupe_key)
                        correct_size = len(deduped_arr) == bound
                        if correct_size and deduped_arr not in seen:
                            seen.add(deduped_arr)
                            yield SamplingResult.joined(
                                deduped_arr,
                                separator=variant_command.separator,
                            )

    def _get_wildcard(
        self,
        command: WildcardCommand,
        context: SamplingContext,
    ) -> ResultGen:
        # TODO: doesn't support weights
        context = context.with_variables(command.variables)
        values = context.wildcard_manager.get_values(command.wildcard)
        if not values:
            yield from get_wildcard_not_found_fallback(command, context)
            return

        for val in values.iterate_string_values_weighted():
            # Parse and generate prompts from wildcard value
            yield from context.sample_prompts(val)

    def _get_literal(
        self,
        command: LiteralCommand,
        context: SamplingContext,
    ) -> ResultGen:
        yield SamplingResult(text=command.literal)
