from __future__ import annotations

import dataclasses
import logging
import re

from dynamicprompts.commands import Command
from dynamicprompts.enums import SamplingMethod

log = logging.getLogger(__name__)

WRAP_MARKER_CHARACTERS = {
    "\u1801",  # Mongolian ellipsis
    "\u2026",  # Horizontal ellipsis
    "\u22ee",  # Vertical ellipsis
    "\u22ef",  # Midline horizontal ellipsis
    "\u22f0",  # Up right diagonal ellipsis
    "\u22f1",  # Down right diagonal ellipsis
    "\ufe19",  # Presentation form for vertical horizontal ellipsis
}

WRAP_MARKER_RE = re.compile(
    f"[{''.join(WRAP_MARKER_CHARACTERS)}]+"  # One or more wrap marker characters
    "|"
    r"\.{3,}",  # ASCII ellipsis of 3 or more dots
)


def split_wrapper_string(s: str) -> tuple[str, str]:
    """
    Split a string into a prefix and suffix at the first wrap marker.
    """
    match = WRAP_MARKER_RE.search(s)
    if match is None:
        log.warning("Found no wrap marker in string %r", s)
        return s, ""
    else:
        return s[: match.start()], s[match.end() :]


@dataclasses.dataclass(frozen=True)
class WrapCommand(Command):
    wrapper: Command
    inner: Command
    sampling_method: SamplingMethod | None = None
