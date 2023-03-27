from __future__ import annotations

import dataclasses
from fnmatch import fnmatch
from typing import Iterable

from dynamicprompts.wildcards.collection import WildcardCollection
from dynamicprompts.wildcards.tree.node import WildcardTreeNode


@dataclasses.dataclass(frozen=True)
class WildcardTree:
    root: WildcardTreeNode = dataclasses.field(default_factory=WildcardTreeNode)
    map: dict[str, WildcardCollection] = dataclasses.field(default_factory=dict)

    def __post_init__(self):
        if not self.map:
            self.update_file_map()

    def update_file_map(self) -> None:
        self.map.clear()
        self.map.update(self.root.walk_items())

    @classmethod
    def from_map(cls, map: dict[str, WildcardCollection]) -> WildcardTree:
        """
        Build a WildcardTree from a map of paths to WildcardCollections.
        """
        root = WildcardTreeNode("")
        for path, collection in map.items():
            parts = path.split("/")
            node = root
            for part in parts[:-1]:
                if part not in node.child_nodes:
                    node.child_nodes[part] = WildcardTreeNode(node.qualify_name(part))
                node = node.child_nodes[part]
            node.collections[parts[-1]] = collection
        return cls(root, map=map.copy())

    def get_collection(self, path: str) -> WildcardCollection:
        return self.map[path]

    def match_collections(self, pattern: str) -> Iterable[WildcardCollection]:
        for name, coll in self.map.items():
            if fnmatch(name, pattern):
                yield coll

    def get_collection_names(self) -> Iterable[str]:
        return self.map.keys()
