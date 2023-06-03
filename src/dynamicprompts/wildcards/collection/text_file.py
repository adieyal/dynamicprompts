from __future__ import annotations

from pathlib import Path

from dynamicprompts.constants import DEFAULT_ENCODING
from dynamicprompts.utils import is_empty_line
from dynamicprompts.wildcards.collection.base import WildcardCollection


class WildcardTextFile(WildcardCollection):
    """
    A wildcard collection that is stored in a text file.
    """

    def __init__(
        self,
        path: Path,
        encoding: str = DEFAULT_ENCODING,
    ) -> None:
        self._path = path
        self._encoding = encoding
        self._cache: list[str] | None = None

    def __repr__(self) -> str:
        return f"<TxtWildcardFile: {self._path}>"

    def get_values(self) -> list[str]:
        if self._cache is not None:
            return self._cache

        with self._path.open(encoding=self._encoding, errors="ignore") as f:
            lines = [line.strip() for line in f if not is_empty_line(line)]
            self._cache = lines
            return self._cache

    def read_text(self) -> str:
        """
        Read the file's raw contents as a string.
        """
        return self._path.read_text(encoding=self._encoding, errors="ignore")

    def write_text(self, contents: str) -> None:
        """
        Rewrite the file's contents with the given string.
        """
        self._path.write_text(contents, encoding=self._encoding)
        self._cache = None
