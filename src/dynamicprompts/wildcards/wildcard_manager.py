from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from dynamicprompts.parser.config import default_parser_config
from dynamicprompts.wildcards.collection import WildcardCollection
from dynamicprompts.wildcards.item import WildcardItem
from dynamicprompts.wildcards.tree import (
    WildcardTree,
    build_tree_from_root_map,
)
from dynamicprompts.wildcards.utils import clean_wildcard
from dynamicprompts.wildcards.values import WildcardValues

if TYPE_CHECKING:
    from dynamicprompts.wildcards.types import RootMap

logger = logging.getLogger(__name__)


class WildcardManager:
    def __init__(
        self,
        path: Path | str | None = None,
        wildcard_wrap=default_parser_config.wildcard_wrap,
        *,
        root_map: RootMap | None = None,
    ) -> None:
        """
        Initialize a wildcard manager.

        You can pass in either a single Path to a directory, or a root map dictionary.
        """
        self._path: Path | None = Path(path) if path else None
        self._wildcard_wrap = wildcard_wrap
        self._tree: WildcardTree | None = None
        self._values_cache: dict[str, WildcardValues] = {}
        self._sort_wildcards = True
        self._dedup_wildcards = True
        self.shuffle_wildcards = False
        self._root_map = {}
        if root_map:
            if self._path:
                raise ValueError("Cannot specify both path and roots")
            self._root_map = root_map
        elif self._path:
            self._root_map = {"": [self._path]}

    @property
    def sort_wildcards(self) -> bool:
        """
        Whether to sort wildcard values.
        """
        return self._sort_wildcards

    @sort_wildcards.setter
    def sort_wildcards(self, value: bool) -> None:
        self._sort_wildcards = value
        self.clear_cache()

    @property
    def dedup_wildcards(self) -> bool:
        """
        Whether to deduplicate wildcard values.
        """
        return self._dedup_wildcards

    @dedup_wildcards.setter
    def dedup_wildcards(self, value: bool) -> None:
        self._dedup_wildcards = value
        self.clear_cache()

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

        If the tree has not been built yet, it will be built from the configured root(s).
        """
        if self._tree is None:
            self._tree = build_tree_from_root_map(self._root_map)
        return self._tree

    def clear_cache(self) -> None:
        """
        Clear the cache of the wildcard manager.
        """
        self._tree = None
        self._values_cache.clear()

    def match_collections(self, wildcard: str) -> Iterable[WildcardCollection]:
        """
        Find `WildcardCollection` objects that match the given glob pattern.
        """
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
        warnings.warn(
            "WildcardManager.get_all_values is deprecated; "
            "use get_values instead to get a WildcardValues object "
            "that supports weighted wildcards.",
            DeprecationWarning,
        )
        return list(self.get_values(wildcard).string_values)

    def get_values(self, wildcard: str) -> WildcardValues:
        """
        Get all wildcard values matching the given wildcard pattern.
        """
        values = self._get_values(wildcard)

        if self.shuffle_wildcards:
            values = values.shuffled()

        return values

    def _get_values(self, wildcard: str) -> WildcardValues:
        """
        Get all wildcard values matching the given wildcard pattern.
        """
        if wildcard in self._values_cache:
            return self._values_cache[wildcard]

        values: list[str | WildcardItem] = []
        for f in self.match_collections(wildcard):
            values.extend(f.get_values())
        if not values and not wildcard.startswith("**"):
            # If the wildcard doesn't match anything, try again with a recursive wildcard
            rec_wildcard = f"**/{wildcard}"
            rec_colls = list(self.match_collections(rec_wildcard))
            for f in rec_colls:
                values.extend(f.get_values())
            if values:
                logger.warning(
                    "No matches for wildcard %r, used %r to match %s",
                    wildcard,
                    rec_wildcard,
                    ", ".join(str(coll) for coll in rec_colls),
                )

        wildcards = list(values)

        if self.dedup_wildcards:
            wildcards = list(dict.fromkeys(wildcards, None))

        if self.sort_wildcards and not self.shuffle_wildcards:
            wildcards = sorted(wildcards, key=str)

        values_object = WildcardValues.from_items(wildcards)

        if len(self._values_cache) > 100:
            # Naive way to limit the size of the cache.
            # We can't use `popitem` because it's guaranteed to be LIFO and we'd want FIFO.
            self._values_cache.clear()

        self._values_cache[wildcard] = values_object

        return values_object
