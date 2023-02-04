from __future__ import annotations

import logging
from random import Random

from dynamicprompts.commands.base import SamplingMethod
from dynamicprompts.generators.promptgenerator import PromptGenerator
from dynamicprompts.samplers.random import DEFAULT_RANDOM
from dynamicprompts.samplers.sampler_manager import ConcreteSamplerManager
from dynamicprompts.wildcardmanager import WildcardManager

logger = logging.getLogger(__name__)


class RandomPromptGenerator(PromptGenerator):
    def __init__(
        self,
        wildcard_manager: WildcardManager,
        seed: int | None = None,
        unlink_seed_from_prompt: bool = False,
        ignore_whitespace: bool = False,
    ) -> None:
        self._wildcard_manager = wildcard_manager
        self._unlink_seed_from_prompt = unlink_seed_from_prompt

        if self._unlink_seed_from_prompt:
            self._random = DEFAULT_RANDOM
        else:
            self._random = Random()
            if seed is not None:
                self._random.seed(seed)

        self._sampler = ConcreteSamplerManager(
            wildcard_manager=wildcard_manager,
            default_sampling_method=SamplingMethod.RANDOM,
            ignore_whitespace=ignore_whitespace,
        )

    def generate(
        self,
        template: str | None,
        num_images: int = 1,
    ) -> list[str]:
        if template is None or len(template) == 0:
            return [""]
        return list(self._sampler.sample_prompts(template, num_images))
