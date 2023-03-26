from __future__ import annotations

import re
from random import Random

DEFAULT_ENCODING = "utf-8"
DEFAULT_COMBO_JOINER = ","
MAX_IMAGES = 1000
WILDCARD_SUFFIX = "txt"
DEFAULT_RANDOM = Random()

# A1111 special syntax (LoRA, hypernet, etc.)
A1111_SPECIAL_SYNTAX_RE = re.compile(r"\s*<[^>]+>")
