from __future__ import annotations

from typing import Iterable

from dynamicprompts.commands import Command
from dynamicprompts.samplers.base import SamplerRouter
from dynamicprompts.types import CommandList, StringGen


class CommandCollection:
    """
    A class that holds a collection of commands and manages generating values for them.
    """

    def __init__(self, commands: Iterable[Command], sampler_router: SamplerRouter):
        self._commands = list(commands)
        self._generators = [
            sampler_router.generator_from_command(c) for c in self._commands
        ]
        self._values: list[str | None] = [next(g) for g in self._generators]
        self._sampler_router = sampler_router

    def get_value(self, command: Command) -> str | None:
        if command not in self._commands:
            raise ValueError(f"Command {command} not in collection")
        index = self._commands.index(command)
        generator = self._generators[index]
        value = self._values[index]

        try:
            self._values[index] = next(generator)
        except StopIteration:
            self._values[index] = None

        return value

    @property
    def commands(self) -> CommandList:
        return self._commands

    @property
    def generators(self) -> list[StringGen]:
        return self._generators
