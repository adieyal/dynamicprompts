from __future__ import annotations

import dataclasses

from dynamicprompts.commands import Command


@dataclasses.dataclass(frozen=True)
class VariableAssignmentCommand(Command):
    name: str
    value: Command
    immediate: bool
    overwrite: bool = True
    sampling_method = None


@dataclasses.dataclass(frozen=True)
class VariableAccessCommand(Command):
    name: str
    default: Command | None = None
    sampling_method = None
