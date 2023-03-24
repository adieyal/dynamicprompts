from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable


class WildcardFile(ABC):
    @property
    def name(self) -> str:
        raise NotImplementedError("...")

    @abstractmethod
    def get_wildcards(self) -> Iterable[str]:
        raise NotImplementedError("...")
