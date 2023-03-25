from __future__ import annotations

import json
import logging
import warnings
from pathlib import Path
from typing import Iterable

from dynamicprompts.constants import DEFAULT_ENCODING
from dynamicprompts.wildcards.collection.base import WildcardCollection
from dynamicprompts.wildcards.collection.list import ListWildcardCollection

log = logging.getLogger(__name__)


def _parse_structured_file_dict(
    data: dict,
    *,
    file_path: Path,
    prefix: tuple[str, ...] = (),
) -> Iterable[tuple[str, WildcardCollection]]:
    """
    Parse a single dict level in a structured file (JSON or YAML) and yield the wildcard collections.
    """
    for name, value in data.items():
        if not isinstance(name, str):
            continue
        prefix_and_name = (*prefix, name)
        name = "/".join(prefix_and_name)
        if isinstance(value, list) and all(isinstance(x, str) for x in value):
            yield (
                name,
                ListWildcardCollection(entries=value, source=(file_path, name)),
            )
        elif isinstance(value, dict):
            yield from _parse_structured_file_dict(
                value,
                file_path=file_path,
                prefix=prefix_and_name,
            )
        else:
            log.warning(
                "Wildcard file %s has unsupported value for key %s",
                file_path,
                name,
            )


def parse_structured_file(file_path: Path) -> Iterable[tuple[str, WildcardCollection]]:
    """
    Parse a structured file (JSON or YAML) and yield the wildcard collections.
    """
    content = file_path.read_text(encoding=DEFAULT_ENCODING)

    if file_path.suffix == ".yaml":
        try:
            import yaml

            data = yaml.safe_load(content)
        except ImportError:  # pragma: no cover
            warnings.warn("YAML support is not available, skipping YAML wildcard file")
            return ()
    elif file_path.suffix == ".json":
        data = json.loads(content)
    else:  # pragma: no cover
        raise ValueError(f"Unexpected file extension: {file_path.suffix}")

    if isinstance(data, dict):
        return _parse_structured_file_dict(data, file_path=file_path)
    if isinstance(data, list):
        # See if the data is a flat list of strings
        valid_entries = [e for e in data if isinstance(e, str)]
        if valid_entries:
            # Only return a collection if it's not empty.
            collection = ListWildcardCollection(
                entries=valid_entries,
                source=file_path,
            )
            return [(file_path.with_suffix("").name, collection)]
    return ()
