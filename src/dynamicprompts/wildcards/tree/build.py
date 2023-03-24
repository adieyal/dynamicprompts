from __future__ import annotations

import os
from pathlib import Path

from dynamicprompts.wildcards.collection import WildcardCollection, WildcardTextFile
from dynamicprompts.wildcards.tree.tree import WildcardTree


def _get_wildcard_file_name_from_path(path: Path, root_path: Path):
    return str(path.relative_to(root_path).with_suffix("")).replace(os.sep, "/")


def build_tree_from_path(root_path: Path) -> WildcardTree:
    """
    Walk a directory tree to build a WildcardTree.

    :param root_path: Root filesystem path.
    """
    path_to_file: dict[str, WildcardCollection] = {}

    for dirname, dirnames, filenames in os.walk(root_path, followlinks=True):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for filename in filenames:
            if filename.endswith(".txt"):
                file_path = Path(dirname) / filename
                name = _get_wildcard_file_name_from_path(file_path, root_path)
                path_to_file[name] = WildcardTextFile(file_path)
    return WildcardTree.from_map(path_to_file)
