from __future__ import annotations

import logging
import typing
from random import Random

from dynamicprompts.commands import (
    Command,
    LiteralCommand,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.parser.config import ParserConfig, default_parser_config
from dynamicprompts.samplers.base import Sampler
from dynamicprompts.wildcardmanager import WildcardManager

logger = logging.getLogger(__name__)

DEFAULT_RANDOM = Random()


def _get_random_variant(
    generator: Sampler,
    variant_command: VariantCommand,
    random: Random,
) -> typing.Generator[str, None, None]:
    if len(variant_command.values) == 0:
        return
    elif len(variant_command.values) == 1:
        yield from generator.generator_from_command(variant_command.values[0])
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
                generator.generator_from_command(c) for c in selected_commands
            ]
            yield variant_command.separator.join(
                next(subgen) for subgen in sub_generators
            )


class RandomSampler(Sampler):
    def __init__(
        self,
        *,
        wildcard_manager: WildcardManager,
        ignore_whitespace: bool = False,
        rand: Random = DEFAULT_RANDOM,
        parser_config: ParserConfig = default_parser_config,
    ):
        super().__init__(
            wildcard_manager=wildcard_manager,
            ignore_whitespace=ignore_whitespace,
            parser_config=parser_config,
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
            values = self._wildcard_manager.get_all_values(command.wildcard)
            while True:
                if len(values) == 0:
                    logger.warning(f"No values found for wildcard {command.wildcard}")
                    yield f"__{command.wildcard}__"
                else:
                    value = self._random.choice(values)
                    # Parse and generate prompts from wildcard value
                    yield from self.generate_prompts(value, 1)
        else:
            raise NotImplementedError(
                f"{self.__class__.__qualname__}: Not implemented: {command}",
            )
