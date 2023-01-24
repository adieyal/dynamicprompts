from __future__ import annotations

import logging
import os
from pathlib import Path

from dynamicprompts import constants
from dynamicprompts.wildcardfile import WildcardFile

logger = logging.getLogger(__name__)


def _normalize_wildcard(wildcard: str):
    return wildcard.strip("_").replace("/", os.sep).replace("\\", os.sep)


class WildcardManager:
    def __init__(self, path: Path):
        self._path = path

    @property
    def path(self) -> Path:
        """
        The root path of the wildcard manager.
        """
        return self._path

    def _directory_exists(self) -> bool:
        return self._path.is_dir()

    def ensure_directory(self):
        try:
            self._path.mkdir(parents=True, exist_ok=True)
        except Exception:
            logger.exception(f"Failed to create directory {self._path}")

    def get_files(self, relative: bool = False) -> list[Path]:
        if not self._directory_exists():
            return []

        files = self._path.rglob(f"*.{constants.WILDCARD_SUFFIX}")
        if relative:
            files = [f.relative_to(self._path) for f in files]

        return list(files)

    def match_files(self, wildcard: str) -> list[WildcardFile]:
        wildcard = _normalize_wildcard(wildcard)
        return [
            WildcardFile(path)
            for path in self._path.rglob(f"{wildcard}.{constants.WILDCARD_SUFFIX}")
        ]

    def wildcard_to_path(self, wildcard: str) -> Path:
        return (self._path / _normalize_wildcard(wildcard)).with_suffix(
            f".{constants.WILDCARD_SUFFIX}"
        )

    def path_to_wildcard(self, path: Path) -> str:
        rel_path = path.relative_to(self._path)
        return f"__{str(rel_path.with_suffix('')).replace(os.sep, '/')}__"

    def get_wildcards(self) -> list[str]:
        files = self.get_files(relative=True)
        return [self.path_to_wildcard(f) for f in files]

    def get_all_values(self, wildcard: str) -> list[str]:
        files = self.match_files(wildcard)
        return sorted(set().union(*[f.get_wildcards() for f in files]))

    def get_wildcard_hierarchy(self, path: Path | None = None):
        if path is None:
            path = self._path

        files = path.glob(f"*.{constants.WILDCARD_SUFFIX}")
        wildcards = sorted(self.path_to_wildcard(f) for f in files)
        directories = sorted(d for d in path.iterdir() if d.is_dir())

        hierarchy = {d.name: self.get_wildcard_hierarchy(d) for d in directories}
        return (wildcards, hierarchy)

    def is_wildcard(self, text: str) -> bool:
        return text.startswith("__") and text.endswith("__")

    def get_collection_path(self) -> Path:
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
