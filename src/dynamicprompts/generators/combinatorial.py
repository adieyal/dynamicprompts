from __future__ import annotations

import logging
from typing import Iterable

from dynamicprompts import constants
from dynamicprompts.generators.promptgenerator import PromptGenerator
from dynamicprompts.samplers.combinatorial import CombinatorialSampler
from dynamicprompts.wildcardmanager import WildcardManager

logger = logging.getLogger(__name__)


class CombinatorialPromptGenerator(PromptGenerator):
    def __init__(
        self,
        wildcard_manager: WildcardManager,
        ignore_whitespace: bool = False,
    ) -> None:
        self._wildcard_manager = wildcard_manager
        self._sampler = CombinatorialSampler(
            wildcard_manager=wildcard_manager,
            ignore_whitespace=ignore_whitespace,
        )

    def generate(  # type: ignore[override]
        self,
        template: str | None,
        max_prompts: int | None = constants.MAX_IMAGES,
    ) -> Iterable[str]:
        if template is None or len(template) == 0:
            return [""]
        prompts = self._sampler.generate_prompts(template, max_prompts)

        return prompts
