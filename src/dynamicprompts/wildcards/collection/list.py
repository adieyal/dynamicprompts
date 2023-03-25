from __future__ import annotations

import dataclasses
from typing import Any

from dynamicprompts.wildcards.collection.base import WildcardCollection


@dataclasses.dataclass(frozen=True)
class ListWildcardCollection(WildcardCollection):
    """
    A wildcard collection that's just a list of wildcards.

    The default implementation uses this to represent wildcards loaded from
    a structured pantry JSON/YAML file.
    """

    entries: list[str]

    # Implementation-specific hint for the source of the wildcards.
    source: Any = None

    def get_values(self) -> list[str]:
        return self.entries
