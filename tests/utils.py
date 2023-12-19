from __future__ import annotations

from dynamicprompts.commands import Command
from dynamicprompts.sampling_context import SamplingContext


def cross(list1: list[str], list2: list[str], sep=",") -> list[str]:
    return [f"{x}{sep}{y}" for x in list1 for y in list2 if x != y]


def zipstr(list1: list[str], list2: list[str], sep="") -> list[str]:
    return [f"{x}{sep}{y}" for x, y in zip(list1, list2)]


def interleave(list1: list[str], list2: list[str]) -> list[str]:
    new_list = list1 + list2
    new_list[::2] = list1
    new_list[1::2] = list2

    return new_list


def sample_n(cmd: Command, scon: SamplingContext, n: int) -> set[str]:
    """
    Sample until we have n unique prompts.
    """
    seen = set()
    for p in scon.sample_prompts(cmd):
        seen.add(str(p))
        if len(seen) == n:
            break
    return seen
