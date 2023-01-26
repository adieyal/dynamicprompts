from __future__ import annotations


def squash_whitespace(s: str) -> str:
    return " ".join(s.split())


def is_empty_line(line: str | None) -> bool:
    return line is None or line.strip() == "" or line.strip().startswith("#")
