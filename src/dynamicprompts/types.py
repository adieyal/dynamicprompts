from __future__ import annotations

from typing import Generator, Iterable, List

from dynamicprompts.commands import Command
from dynamicprompts.sampling_result import SamplingResult

ResultGen = Generator[SamplingResult, None, None]
ResultIter = Iterable[SamplingResult]
CommandList = List[Command]
CommandListGen = Generator[CommandList, None, None]
StringIter = Iterable[str]


def to_result_gen(values: Iterable[SamplingResult | str]) -> ResultGen:
    for s in values:
        if isinstance(s, SamplingResult):
            yield s
        else:
            assert isinstance(s, str), f"expected str, got {type(s)}"
            yield SamplingResult(text=s)


def to_string_gen(values: Iterable[SamplingResult | str]) -> StringIter:
    for s in values:
        if isinstance(s, SamplingResult):
            yield s.text
        else:
            assert isinstance(s, str), f"expected str, got {type(s)}"
            yield s
