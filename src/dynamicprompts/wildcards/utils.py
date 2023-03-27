from __future__ import annotations

import os

from dynamicprompts.utils import removeprefix, removesuffix


def clean_wildcard(wildcard: str, *, wildcard_wrap: str) -> str:
    """
    Clean, canonicalize, and validate a wildcard string (possibly wrapped with a `wrap`).

    :return: the cleaned wildcard
    """
    wildcard = (
        wildcard.replace("/", os.sep)
        .replace("\\", os.sep)  # normalize path separators
        .rstrip(os.sep)  # remove trailing path separator (likely a typo)
    )
    wildcard = removeprefix(wildcard, wildcard_wrap)
    wildcard = removesuffix(wildcard, wildcard_wrap)

    if wildcard.startswith(os.sep):
        raise ValueError(f"Wildcard {wildcard} cannot start with {os.sep}")
    if ".." in wildcard:
        raise ValueError(f"Wildcard can not contain '..': {wildcard}")
    return wildcard
