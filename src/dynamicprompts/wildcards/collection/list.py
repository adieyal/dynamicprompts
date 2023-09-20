from __future__ import annotations

import dataclasses
from typing import Any, Sequence

from dynamicprompts.wildcards.collection.base import WildcardCollection
from dynamicprompts.wildcards.item import WildcardItem


@dataclasses.dataclass(frozen=True)
class ListWildcardCollection(WildcardCollection):
    """
    A wildcard collection that's just a list of wildcards.

    The default implementation uses this to represent wildcards loaded from
    a structured pantry JSON/YAML file.
    """

    entries: Sequence[str | WildcardItem]

    # Implementation-specific hint for the source of the wildcards.
    source: Any = None

    def get_values(self) -> Sequence[str | WildcardItem]:
        return self.entries
