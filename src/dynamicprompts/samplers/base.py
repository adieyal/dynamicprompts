from __future__ import annotations

import typing
from abc import ABCMeta, abstractmethod
from itertools import islice

from dynamicprompts.commands import Command
from dynamicprompts.parser.parse import parse
from dynamicprompts.utils import squash_whitespace
from dynamicprompts.wildcardmanager import WildcardManager


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

    def generate_prompts(
        self,
        prompt: str | Command,
        num_prompts: int | None = None,
    ) -> typing.Iterable[str]:
        """
        Generate prompts from a prompt template.

        :param prompt: The prompt template to generate prompts from.
        :param num_prompts: How many prompts to generate (at most). If None, generate all possible prompts.
        """
        if not prompt:
            return []
        command: Command
        if isinstance(prompt, str):
            command = parse(prompt)
        elif isinstance(prompt, Command):
            command = prompt
        else:
            raise TypeError(f"Expected prompt to be str or Command, got {type(prompt)}")
        gen = self.generator_from_command(command)

        if self._ignore_whitespace:
            gen = (squash_whitespace(p) for p in gen)

        if num_prompts is None:
            return gen
        return islice(gen, num_prompts)
