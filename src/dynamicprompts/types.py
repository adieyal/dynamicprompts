from __future__ import annotations

from typing import Generator, Iterable, List

from dynamicprompts.commands import Command

StringGen = Generator[str, None, None]
CommandList = List[Command]
CommandListGen = Generator[CommandList, None, None]
StringIter = Iterable[str]
