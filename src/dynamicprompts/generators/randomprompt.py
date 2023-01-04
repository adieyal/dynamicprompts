from __future__ import annotations
from typing import List

import logging
from random import Random
import random

from dynamicprompts import constants
from dynamicprompts.wildcardmanager import WildcardManager
from dynamicprompts.parser.random_generator import RandomGenerator

from . import PromptGenerator

logger = logging.getLogger(__name__)

class RandomPromptGenerator(PromptGenerator):
    def __init__(
        self,
        wildcard_manager: WildcardManager,
        seed: int | None = None,
        unlink_seed_from_prompt: bool = constants.UNLINK_SEED_FROM_PROMPT,
    ):
        self._wildcard_manager = wildcard_manager
        self._unlink_seed_from_prompt = unlink_seed_from_prompt

        if self._unlink_seed_from_prompt:
            self._random = random
        else:
            self._random = Random()
            if seed is not None:
                self._random.seed(seed)

        self._generator = RandomGenerator(wildcard_manager)

    def generate(self, template, max_prompts=constants.MAX_IMAGES) -> List[str]:
        if template is None or len(template) == 0:
            return [""]
        prompts = self._generator.generate_prompts(template, max_prompts)
        prompts = list(prompts)
        return prompts
