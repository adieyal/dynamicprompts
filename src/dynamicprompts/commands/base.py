from __future__ import annotations

from dynamicprompts.enums import SamplingMethod


class Command:
    """Base class for commands."""

    sampling_method: SamplingMethod | None
