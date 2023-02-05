from __future__ import annotations

import logging
import typing
from abc import ABCMeta, abstractmethod

from dynamicprompts.commands import Command, LiteralCommand, SequenceCommand
from dynamicprompts.types import StringGen
from dynamicprompts.utils import rotate_and_join
from dynamicprompts.wildcardmanager import WildcardManager

logger = logging.getLogger(__name__)


class SamplerRouter(metaclass=ABCMeta):
    def generator_from_command(self, command) -> typing.Generator[str, None, None]:
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement generator_from_command",
        )

    @abstractmethod
    def sample_prompts(
        self,
        prompt: str | Command,
        num_prompts: int | None = None,
    ) -> typing.Iterable[str]:
        ...

    def get_combination_generator(
        self,
        combo: list[Command],
    ) -> typing.Generator[list[str], None, None]:
        if len(combo) == 0:
            yield []
        else:
            c_1, c_rest = combo[0], combo[1:]

            for p in self.generator_from_command(c_1):
                for rest_prompt in self.get_combination_generator(c_rest):
                    if rest_prompt:
                        yield [p] + rest_prompt
                    else:
                        yield [p]


class Sampler(metaclass=ABCMeta):
    def __init__(
        self,
        *,
        wildcard_manager: WildcardManager,
        ignore_whitespace: bool = False,
        sampler_manager: SamplerRouter,
    ):
        self._wildcard_manager = wildcard_manager
        self._ignore_whitespace = ignore_whitespace
        self._sampler_manager = sampler_manager

    @abstractmethod
    def generator_from_command(self, command: Command) -> StringGen:
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement generator_from_command",
        )

    def _get_sequence(self, command: SequenceCommand) -> StringGen:
        generate_from_command = self._sampler_manager.generator_from_command
        sub_generators = [generate_from_command(c) for c in command.tokens]

        while True:
            yield rotate_and_join(sub_generators, separator=command.separator)

    def _get_literal(self, command: LiteralCommand):
        while True:
            yield command.literal
