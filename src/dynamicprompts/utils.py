from __future__ import annotations

from collections import OrderedDict


def squash_whitespace(s: str) -> str:
    return " ".join(s.split())


def is_empty_line(line: str | None) -> bool:
    return line is None or line.strip() == "" or line.strip().startswith("#")


def dedupe(arr: list[str]) -> tuple[str, ...]:
    ordered_dict = OrderedDict.fromkeys(arr)
    return tuple(ordered_dict.keys())
