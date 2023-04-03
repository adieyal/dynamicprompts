from __future__ import annotations

import logging
import os
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from dynamicprompts.wildcards.collection import WildcardCollection, WildcardTextFile
from dynamicprompts.wildcards.collection.list import ListWildcardCollection
from dynamicprompts.wildcards.collection.structured import parse_structured_file
from dynamicprompts.wildcards.tree.tree import WildcardTree
from dynamicprompts.wildcards.utils import combine_name_parts

if TYPE_CHECKING:
    from dynamicprompts.wildcards.types import CollectionableItem, RootItem, RootMap

log = logging.getLogger(__name__)


def _get_wildcard_file_name_from_path(path: Path, root_path: Path):
    if path == root_path:
        # Special case, because `with_suffix()` would fail
        return ""
    return str(path.relative_to(root_path).with_suffix("")).replace(os.sep, "/")


def _get_wildcard_collections_from_path(
    *,
    file_path: Path,
    root_path: Path,
) -> Iterable[tuple[str, WildcardCollection]]:
    if file_path.suffix == ".txt":
        name = _get_wildcard_file_name_from_path(file_path, root_path)
        yield (name, WildcardTextFile(file_path))
        return

    if file_path.suffix in (".json", ".yaml"):
        pantry_root_prefix = _get_wildcard_file_name_from_path(
            path=file_path.parent,
            root_path=root_path,
        )
        if pantry_root_prefix:
            # Suffix the / here, so we don't need to worry about pantries
            # in the root later
            pantry_root_prefix += "/"
        try:
            for name, wildcard_file in parse_structured_file(file_path):
                yield (f"{pantry_root_prefix}{name}", wildcard_file)
        except Exception as exc:  # pragma: no cover
            log.warning(
                "Unable to read structured wildcard file %s: %s",
                file_path,
                exc,
            )


def build_tree_from_path(root_path: Path) -> WildcardTree:
    """
    Walk a directory tree to build a WildcardTree.

    :param root_path: Root filesystem path.
    """
    path_to_file: dict[str, WildcardCollection] = {}

    for dirname, dirnames, filenames in os.walk(root_path, followlinks=True):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for filename in filenames:
            path_to_file.update(
                _get_wildcard_collections_from_path(
                    file_path=Path(dirname) / filename,
                    root_path=root_path,
                ),
            )
    return WildcardTree.from_map(path_to_file)


def build_tree_from_root_map(root_map: RootMap) -> WildcardTree:
    collection_map: dict[str, WildcardCollection] = {}
    for root, items in root_map.items():
        for item in items:
            for name, collection_or_list in _mappingify_item(item).items():
                collection = _collectionify(collection_or_list)
                collection_map[combine_name_parts(root, name)] = collection
    return WildcardTree.from_map(collection_map)


def _collectionify(collection_or_list: CollectionableItem) -> WildcardCollection:
    if isinstance(collection_or_list, list):
        return ListWildcardCollection([str(x) for x in collection_or_list])
    return collection_or_list


def _mappingify_item(item: RootItem) -> dict[str, CollectionableItem]:
    if isinstance(item, Path):
        if item.is_dir():
            return dict(build_tree_from_path(item).map)
        warnings.warn(f"Root {item} is not a directory, skipping")
        return {}
    return item
