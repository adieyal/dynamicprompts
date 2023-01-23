from __future__ import annotations


def squash_whitespace(s):
    return " ".join(s.split())


def is_empty_line(line):
    return line is None or line.strip() == "" or line.strip().startswith("#")
