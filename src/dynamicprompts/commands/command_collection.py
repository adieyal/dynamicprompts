from typing import Iterable

from dynamicprompts.commands import Command
from dynamicprompts.samplers.base import SamplerRouter


class CommandCollection:
    def __init__(self, commands: Iterable[Command], sampler_manager: SamplerRouter):
        self._sampler_manager = sampler_manager
        self._commands = list(commands)
        self._generators = [
            self._sampler_manager.generator_from_command(c) for c in self._commands
        ]
        self._values = [next(g) for g in self._generators]

    def get_value(self, command: Command) -> str:
        if command not in self._commands:
            raise ValueError(f"Command {command} not in collection")
        index = self._commands.index(command)
        generator = self._generators[index]
        value = self._values[index]

        self._values[index] = next(generator)

        return value
