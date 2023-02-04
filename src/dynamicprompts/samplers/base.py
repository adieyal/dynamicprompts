from __future__ import annotations

import typing
from abc import ABCMeta, abstractmethod

from dynamicprompts.commands import Command
from dynamicprompts.wildcardmanager import WildcardManager


class SamplerManager(metaclass=ABCMeta):
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
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement sample_prompts",
        )

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
    ):
        self._wildcard_manager = wildcard_manager
        self._ignore_whitespace = ignore_whitespace

    @abstractmethod
    def generator_from_command(
        self,
        command: Command,
    ) -> typing.Generator[str, None, None]:
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement generator_from_command",
        )
