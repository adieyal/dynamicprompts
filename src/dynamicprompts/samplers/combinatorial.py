from __future__ import annotations

import typing

from dynamicprompts.commands import (
    Command,
    LiteralCommand,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.samplers.base import Sampler, SamplerManager
from dynamicprompts.types import StringGen
from dynamicprompts.wildcardmanager import WildcardManager


def _dedupe(arr: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for item in arr:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return tuple(result)


def _combo_to_prompt(
    sampler_manager: SamplerManager,
    combo: list[Command],
) -> typing.Iterable[list[str]]:
    if len(combo) == 0:
        yield []
        return

    c_1, c_rest = combo[0], combo[1:]

    for p in sampler_manager.generator_from_command(c_1):
        for rest_prompt in _combo_to_prompt(sampler_manager, c_rest):
            if rest_prompt:
                yield [p] + rest_prompt
            else:
                yield [p]


class CombinatorialSampler(Sampler):
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
            sampler_manager=sampler_manager,
        )
        self._sampler_manager = sampler_manager

    def _get_combinatorial_sequence(
        self,
        tokens: list[Command],
        *,
        separator: str,
    ) -> typing.Iterable[str]:

        if not tokens:
            yield ""
            return

        token = tokens[0]
        for prompt in self._sampler_manager.generator_from_command(token):
            for next_prompts in self._get_combinatorial_sequence(
                tokens[1:],
                separator=separator,
            ):
                res = prompt + separator + next_prompts
                yield res

    def _get_combinatorial_variant(
        self,
        variant_command: VariantCommand,
    ) -> typing.Iterable[str]:

        if len(variant_command.variants) == 0:
            return []

        seen = set()

        for bound in range(variant_command.min_bound, variant_command.max_bound + 1):
            for combo in variant_command.get_value_combinations(bound):
                for prompt_arr in _combo_to_prompt(self._sampler_manager, combo):
                    deduped_arr = _dedupe(prompt_arr)
                    correct_size = len(deduped_arr) == bound
                    if correct_size and deduped_arr not in seen:
                        seen.add(deduped_arr)
                        yield variant_command.separator.join(deduped_arr)

    def _get_combinatorial_wildcard(self, command: WildcardCommand):
        for val in self._wildcard_manager.get_all_values(command.wildcard):
            # Parse and generate prompts from wildcard value
            yield from self._sampler_manager.sample_prompts(val)

    def generator_from_command(
        self,
        command: Command,
    ) -> StringGen:
        if isinstance(command, LiteralCommand):
            yield command.literal
        elif isinstance(command, SequenceCommand):
            yield from self._get_combinatorial_sequence(
                command.tokens,
                separator=command.separator,
            )
        elif isinstance(command, VariantCommand):
            yield from self._get_combinatorial_variant(command)
        elif isinstance(command, WildcardCommand):
            yield from self._get_combinatorial_wildcard(command)
        else:
            raise NotImplementedError(
                f"{self.__class__.__name__} does not support {command.__class__.__name__}",
            )
