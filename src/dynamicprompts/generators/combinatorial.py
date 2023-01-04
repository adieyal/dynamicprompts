from __future__ import annotations

import logging
from typing import List

from dynamicprompts.wildcardmanager import WildcardManager
from dynamicprompts import constants
from dynamicprompts.parser.combinatorial_generator import CombinatorialGenerator
from . import PromptGenerator

logger = logging.getLogger(__name__)


class CombinatorialPromptGenerator(PromptGenerator):
    def __init__(self, wildcard_manager: WildcardManager):
        self._wildcard_manager = wildcard_manager
        self._generator = CombinatorialGenerator(wildcard_manager)

    def generate(self, template, max_prompts=constants.MAX_IMAGES) -> List[str]:
        if template is None or len(template) == 0:
            return [""]
        prompts = self._generator.generate_prompts(template, max_prompts)
        prompts = list(prompts)

        return prompts
