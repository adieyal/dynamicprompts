from __future__ import annotations

import dataclasses
from typing import Iterable


@dataclasses.dataclass(frozen=True)
class SamplingResult:
    """
    An internal result of a sampling. May contain metadata in the future.
    """

    text: str

    def __str__(self):
        return self.text

    @property
    def dedupe_key(self) -> tuple[str]:
        # Used by e.g. combinatorial sampling's fragment deduplication.
        # Please make sure to update this if you add more fields to SamplingResult.
        return (self.text,)

    def whitespace_squashed(self) -> SamplingResult:
        from dynamicprompts.utils import squash_whitespace

        return dataclasses.replace(self, text=squash_whitespace(self.text))

    @classmethod
    def joined(
        cls,
        results: Iterable[SamplingResult],
        *,
        separator: str,
    ) -> SamplingResult:
        from dynamicprompts.utils import removeprefix, removesuffix

        joined = separator.join(r.text for r in results)
        if separator:
            joined = removeprefix(joined, separator)
            joined = removesuffix(joined, separator)
        return cls(text=joined)
