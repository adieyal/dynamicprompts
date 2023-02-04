from __future__ import annotations

from typing import Generator, List

from dynamicprompts.commands import Command

StringGen = Generator[str, None, None]
CommandList = List[Command]
