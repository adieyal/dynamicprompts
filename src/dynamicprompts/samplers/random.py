from __future__ import annotations

import logging
from random import Random
from typing import Iterable

from dynamicprompts.commands import (
    Command,
    LiteralCommand,
    SamplingMethod,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.parser.config import ParserConfig, default_parser_config
from dynamicprompts.samplers.base import Sampler, SamplerRouter
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
        sampler_router: SamplerRouter,
        rand: Random = DEFAULT_RANDOM,
        parser_config: ParserConfig = default_parser_config,
    ):
        super().__init__(
            wildcard_manager=wildcard_manager,
            ignore_whitespace=ignore_whitespace,
            sampler_router=sampler_router,
            parser_config=parser_config,
        )
        self._sampler_router = sampler_router
        self._random = rand

    def _get_variant_choices(
        self,
        values: list[Command],
        weights: list[float],
        num_choices,
    ) -> list[Command]:
        # Wraps choose_without_replacement for ease of testing
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
        self._propagate_sampling_method(variant_command.values)

        if len(variant_command.values) == 0:
            return
        elif len(variant_command.values) == 1:
            yield from self._sampler_router.generator_from_command(
                variant_command.values[0],
            )
        else:
            while True:
                num_choices = self._random.randint(
                    variant_command.min_bound,
                    variant_command.max_bound,
                )

                selected_commands = self._get_variant_choices(
                    variant_command.values,
                    weights=variant_command.weights,
                    num_choices=num_choices,
                )
                sub_generators = [
                    self._sampler_router.generator_from_command(c)
                    for c in selected_commands
                ]

                if len(sub_generators) == 0:
                    yield ""
                else:
                    yield rotate_and_join(
                        sub_generators,
                        separator=variant_command.separator,
                    )

    def _get_random_wildcard(self, command: WildcardCommand) -> StringGen:
        values = self._wildcard_manager.get_all_values(command.wildcard)

        if len(values) == 0:
            logger.warning(f"No values found for wildcard {command.wildcard}")

        while True:
            if len(values) == 0:
                yield f"__{command.wildcard}__"
            else:
                value = self._random.choice(values)
                yield from self._sampler_router.sample_prompts(value, 1)

    def _propagate_sampling_method(self, commands: Iterable[Command]) -> None:
        for cmd in commands:
            if cmd.sampling_method == SamplingMethod.DEFAULT or (
                cmd.sampling_method is not None
                and not cmd.sampling_method.is_nonfinite()
            ):
                cmd.sampling_method = SamplingMethod.RANDOM

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
