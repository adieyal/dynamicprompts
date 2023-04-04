from __future__ import annotations

import dataclasses
from typing import Iterable

from dynamicprompts.wildcards.collection import WildcardCollection
from dynamicprompts.wildcards.utils import combine_name_parts


@dataclasses.dataclass(frozen=True)
class WildcardTreeNode:
    path: str = ""
    child_nodes: dict[str, WildcardTreeNode] = dataclasses.field(default_factory=dict)
    collections: dict[str, WildcardCollection] = dataclasses.field(default_factory=dict)

    def get_items(self) -> Iterable[tuple[str, WildcardCollection]]:
        """
        Get the collection items (pair of full path -> collection) of this node.
        """
        for name, file in self.collections.items():
            yield (self.qualify_name(name), file)

    def qualify_name(self, name: str) -> str:
        """
        Qualify a collection name with the path of this node.
        """
        return combine_name_parts(self.path, name)

    def get_full_names(self) -> Iterable[str]:
        """
        Get the full paths of the files in this node.
        """
        for name in self.collections:
            yield self.qualify_name(name)

    def walk_items(self) -> Iterable[tuple[str, WildcardCollection]]:
        """
        Walk the items (pair of full path -> collection) of this node and its children.
        """
        yield from self.get_items()
        for child in self.child_nodes.values():
            yield from child.walk_items()

    def walk_full_names(self) -> Iterable[str]:
        """
        Walk the full paths of the collections in this node and its children.
        """
        yield from self.get_full_names()
        for child in self.child_nodes.values():
            yield from child.walk_full_names()
