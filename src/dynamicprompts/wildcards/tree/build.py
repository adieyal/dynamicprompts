from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterable

from dynamicprompts.wildcards.collection import WildcardCollection, WildcardTextFile
from dynamicprompts.wildcards.collection.structured import parse_structured_file
from dynamicprompts.wildcards.tree.tree import WildcardTree

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
