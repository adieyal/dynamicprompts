from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

from dynamicprompts.parser.config import default_parser_config
from dynamicprompts.wildcards.collection import WildcardCollection
from dynamicprompts.wildcards.tree import (
    WildcardTree,
    build_tree_from_path,
)
from dynamicprompts.wildcards.utils import clean_wildcard

logger = logging.getLogger(__name__)


class WildcardManager:
    def __init__(
        self,
        path: Path | str | None = None,
        wildcard_wrap=default_parser_config.wildcard_wrap,
    ) -> None:
        self._path: Path | None = Path(path) if path else None
        self._wildcard_wrap = wildcard_wrap
        self._tree: WildcardTree | None = None

    @property
    def path(self) -> Path | None:
        """
        The root path of the wildcard manager, if set.
        """
        return self._path

    @property
    def wildcard_wrap(self) -> str:
        """
        The string that is used as the prefix and suffix of a wildcard
        the default is "__" (two underscores)
        """
        return self._wildcard_wrap

    def to_wildcard(self, name: str) -> str:
        """
        Wrap `name` in the wildcard wrap string if it is not already wrapped.
        """
        ww = self._wildcard_wrap
        if not name.startswith(ww):
            name = f"{ww}{name}"
        if not name.endswith(ww):
            name = f"{name}{ww}"
        return name

    def is_wildcard(self, text: str) -> bool:
        """
        Check if `text` is a wildcard reference (i.e. starts and ends with the wildcard wrap string)
        """
        return text.startswith(self.wildcard_wrap) and text.endswith(self.wildcard_wrap)

    @property
    def tree(self) -> WildcardTree:
        """
        Get the wildcard tree.

        If the tree has not been built yet, it will be built from the configured path.
        """
        if self._tree is None:
            self._tree = (
                build_tree_from_path(self._path)
                if self._path and self._directory_exists()
                else WildcardTree()
            )
        return self._tree

    def clear_cache(self) -> None:
        """
        Clear the cache of the wildcard manager.
        """
        self._tree = None

    def _directory_exists(self) -> bool:
        return bool(self._path and self._path.is_dir())

    def match_collections(self, wildcard: str) -> Iterable[WildcardCollection]:
        """
        Find `WildcardCollection` objects that match the given glob pattern.
        """
        if not self._path:
            return []
        try:
            wildcard = clean_wildcard(wildcard, wildcard_wrap=self._wildcard_wrap)
        except ValueError:
            logger.warning(f"Invalid wildcard: {wildcard}", exc_info=True)
            return []
        return self.tree.match_collections(wildcard)

    def get_file(self, name: str) -> WildcardCollection:
        """
        Get a single wildcard collection by full name; raise an exception if there is no match.
        """
        name = clean_wildcard(name, wildcard_wrap=self._wildcard_wrap)
        return self.tree.get_collection(name)

    def get_collection_names(self) -> set[str]:
        """
        Get the names of all known wildcard collections.
        """
        return set(self.tree.get_collection_names())

    def get_all_values(self, wildcard: str) -> list[str]:
        """
        Get all wildcard values matching the given wildcard pattern.
        """
        values: set[str] = set()
        for f in self.match_collections(wildcard):
            values.update(f.get_values())
        return sorted(values)
