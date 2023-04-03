from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TypeAlias, Union

    from dynamicprompts.wildcards.collection import WildcardCollection

    CollectionableItem: TypeAlias = Union[WildcardCollection, list[str]]
    RootItem: TypeAlias = Union[Path, dict[str, CollectionableItem]]
    RootMap: TypeAlias = dict[str, list[RootItem]]
