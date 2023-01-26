from __future__ import annotations

import logging
import random
from random import Random

from dynamicprompts.generators.promptgenerator import PromptGenerator
from dynamicprompts.parser.random_generator import RandomGenerator
from dynamicprompts.wildcardmanager import WildcardManager

logger = logging.getLogger(__name__)


class RandomPromptGenerator(PromptGenerator):
    def __init__(
        self,
        wildcard_manager: WildcardManager,
        seed: int | None = None,
        unlink_seed_from_prompt: bool = False,
        ignore_whitespace=False,
    ):
        self._wildcard_manager = wildcard_manager
        self._unlink_seed_from_prompt = unlink_seed_from_prompt

        if self._unlink_seed_from_prompt:
            self._random = random
        else:
            self._random = Random()
            if seed is not None:
                self._random.seed(seed)

        self._generator = RandomGenerator(
            wildcard_manager,
            rand=self._random,
            ignore_whitespace=ignore_whitespace,
        )

    def generate(self, template, num_images=1) -> list[str]:
        if template is None or len(template) == 0:
            return [""]
        prompts = self._generator.generate_prompts(template, num_images)
        prompts = list(prompts)
        return prompts
