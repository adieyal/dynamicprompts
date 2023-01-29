from __future__ import annotations

import warnings

from dynamicprompts.wildcardmanager import WildcardManager


class ActionBuilder:  # pragma: no cover
    def __init__(self, wildcard_manager: WildcardManager, ignore_whitespace=False):
        warnings.warn(
            "ActionBuilder is deprecated and will be removed in a future version",
            DeprecationWarning,
        )
        self._wildcard_manager = wildcard_manager
        self._ignore_whitespace = ignore_whitespace
