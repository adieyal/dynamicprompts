from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from dynamicprompts import constants
from dynamicprompts.parser.config import default_parser_config
from dynamicprompts.utils import removeprefix, removesuffix
from dynamicprompts.wildcardfile import WildcardFile

logger = logging.getLogger(__name__)


def _is_relative_to(p1: Path, p2: Path) -> bool:
    # Port of Path.is_relative_to from Python 3.9
    try:
        p1.relative_to(p2)
        return True
    except ValueError:
        return False


def _clean_wildcard(wildcard: str, *, wildcard_wrap: str) -> str:
    wildcard = (
        wildcard.replace("/", os.sep)
        .replace("\\", os.sep)  # normalize path separators
        .rstrip(os.sep)  # remove trailing path separator (likely a typo)
    )
    wildcard = removeprefix(wildcard, wildcard_wrap)
    wildcard = removesuffix(wildcard, wildcard_wrap)

    if wildcard.startswith(os.sep):
        raise ValueError(f"Wildcard {wildcard} cannot start with {os.sep}")
    if ".." in wildcard:
        raise ValueError(f"Wildcard can not contain '..': {wildcard}")
    return wildcard


class WildcardManager:
    def __init__(
        self,
        path: Path | None = None,
        wildcard_wrap=default_parser_config.wildcard_wrap,
    ) -> None:
        self._path = path
        self._wildcard_wrap = wildcard_wrap

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

    def _directory_exists(self) -> bool:
        return bool(self._path and self._path.is_dir())

    def ensure_directory(self) -> None:
        if not self._path:
            return
        try:
            self._path.mkdir(parents=True, exist_ok=True)
        except Exception:
            logger.exception(f"Failed to create directory {self._path}")

    def get_files(self, relative: bool = False) -> list[Path]:
        if not (self._path and self._directory_exists()):
            return []

        files = list(self._path.rglob(f"*.{constants.WILDCARD_SUFFIX}"))
        if relative:
            files = [f.relative_to(self._path) for f in files]

        return list(files)

    def match_files(self, wildcard: str) -> list[WildcardFile]:
        if not self._path:
            return []
        try:
            wildcard = _clean_wildcard(wildcard, wildcard_wrap=self._wildcard_wrap)
        except ValueError:
            logger.warning(f"Invalid wildcard: {wildcard}", exc_info=True)
            return []

        return [
            WildcardFile(path, name=self.path_to_wildcard_without_separators(path))
            for path in self._path.rglob(f"{wildcard}.{constants.WILDCARD_SUFFIX}")
            if _is_relative_to(path.absolute(), self._path)
        ]

    def wildcard_to_path(self, wildcard: str) -> Path:
        if not self._path:  # pragma: no cover
            raise ValueError("Can't call wildcard_to_path without a path set")
        return (
            self._path / _clean_wildcard(wildcard, wildcard_wrap=self._wildcard_wrap)
        ).with_suffix(
            f".{constants.WILDCARD_SUFFIX}",
        )

    def path_to_wildcard_without_separators(self, path: Path) -> str:
        if not self._path:  # pragma: no cover
            raise ValueError(
                "Can't call path_to_wildcard_without_separators without a path set",
            )
        rel_path = path.relative_to(self._path)
        return str(rel_path.with_suffix("")).replace(os.sep, "/")

    def path_to_wildcard(self, path: Path) -> str:
        return f"{self._wildcard_wrap}{self.path_to_wildcard_without_separators(path)}{self._wildcard_wrap}"

    def get_wildcards(self) -> list[str]:
        files = self.get_files(relative=True)
        return [self.path_to_wildcard(f) for f in files]

    def get_all_values(self, wildcard: str) -> list[str]:
        files = self.match_files(wildcard)
        return sorted(set().union(*[f.get_wildcards() for f in files]))

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

    # TODO: the return type is actually a recursive type (replace that Any)
    def get_wildcard_hierarchy(
        self,
        path: Path | None = None,
    ) -> tuple[list[str], dict[str, Any]]:
        if path is None:
            path = self._path
        if not path:
            return ([], {})

        files = path.glob(f"*.{constants.WILDCARD_SUFFIX}")
        wildcards = sorted(self.path_to_wildcard(f) for f in files)
        directories = sorted(d for d in path.iterdir() if d.is_dir())

        hierarchy = {d.name: self.get_wildcard_hierarchy(d) for d in directories}
        return (wildcards, hierarchy)

    def is_wildcard(self, text: str) -> bool:
        return text.startswith(self.wildcard_wrap) and text.endswith(self.wildcard_wrap)

    def get_collection_path(self) -> Path:
        if not self._path:  # pragma: no cover
            raise ValueError("Can't call get_collection_path without a path set")
        return self._path.parent / "collections"

    def get_collections(self) -> list[str]:
        return list(self.get_collection_dirs().keys())

    def get_collection_dirs(self) -> dict[str, Path]:
        collection_path = self.get_collection_path()
        collection_dirs = [x for x in collection_path.iterdir() if x.is_dir()]
        collection_names = [
            str(c.relative_to(collection_path)) for c in collection_dirs
        ]

        return dict(zip(collection_names, collection_dirs))
