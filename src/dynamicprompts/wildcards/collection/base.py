from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable


class WildcardCollection(ABC):
    """
    A wildcard collection, i.e. a collection of strings.
    """

    @abstractmethod
    def get_values(self) -> Iterable[str]:
        """
        Get the contents of this collection.
        """
        raise NotImplementedError("...")
