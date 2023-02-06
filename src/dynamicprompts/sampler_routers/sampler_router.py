from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Generator

from dynamicprompts.commands import Command
from dynamicprompts.types import StringGen, StringIter


class SamplerRouter(metaclass=ABCMeta):
    def generator_from_command(self, command) -> StringGen:
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement generator_from_command",
        )

    @abstractmethod
    def sample_prompts(
        self,
        prompt: str | Command,
        num_prompts: int | None = None,
    ) -> StringIter:
        ...

    @abstractmethod
    def clone(
        self,
    ) -> SamplerRouter:
        ...

    def get_combination_generator(
        self,
        combo: list[Command],
    ) -> Generator[list[str], None, None]:
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
