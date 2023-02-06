from __future__ import annotations

import re

DEFAULT_ENCODING = "utf-8"
DEFAULT_COMBO_JOINER = ","
MAX_IMAGES = 1000
WILDCARD_SUFFIX = "txt"
MAX_NOOP_ITERATIONS = 100
WILDCARD_RE = re.compile(r"__(.*?)__")
COMBINATIONS_RE = re.compile(r"\{([^{}]*)}")
