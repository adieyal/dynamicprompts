from __future__ import annotations

import re

from dynamicprompts.utils import removeprefix, removesuffix


def clean_wildcard(wildcard: str, *, wildcard_wrap: str) -> str:
    """
    Clean, canonicalize, and validate a wildcard string (possibly wrapped with a `wrap`).

    :return: the cleaned wildcard
    """

    # remove wrapping
    wildcard = removeprefix(wildcard, wildcard_wrap)
    wildcard = removesuffix(wildcard, wildcard_wrap)

    # normalize path separators to forward slash
    wildcard = re.sub(r"[\\/]+", "/", wildcard)

    # remove leading and trailing path separators (likely a typo)
    wildcard = wildcard.strip("/")

    # validate
    if ".." in wildcard:
        raise ValueError(f"Wildcard can not contain '..': {wildcard}")
    if "\\" in wildcard:
        raise ValueError(f"Wildcard can not contain '\\': {wildcard}")
    return wildcard
