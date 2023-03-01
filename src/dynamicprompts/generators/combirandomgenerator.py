from __future__ import annotations

import logging
from random import Random

from dynamicprompts.generators.promptgenerator import PromptGenerator
from dynamicprompts.parser.config import ParserConfig, default_parser_config
from dynamicprompts.samplers.random import DEFAULT_RANDOM
from dynamicprompts.samplers import CombiRandomSampler
from dynamicprompts.wildcardmanager import WildcardManager

logger = logging.getLogger(__name__)


class CombiRandomPromptGenerator(PromptGenerator):
    def __init__(
        self,
        wildcard_manager: WildcardManager,
        seed: int | None = None,
        unlink_seed_from_prompt: bool = False,
        ignore_whitespace: bool = False,
        parser_config: ParserConfig = default_parser_config,
    ) -> None:
        self._wildcard_manager = wildcard_manager
        self._unlink_seed_from_prompt = unlink_seed_from_prompt

        if self._unlink_seed_from_prompt:
            self._random = DEFAULT_RANDOM
        else:
            self._random = Random()
            if seed is not None:
                self._random.seed(seed)

        self._sampler = CombiRandomSampler(
            wildcard_manager=wildcard_manager,
            rand=self._random,
            ignore_whitespace=ignore_whitespace,
            parser_config=parser_config,
        )

    def generate(
        self,
        template: str | None,
        num_images: int = 1,
    ) -> list[str]:
        if template is None or len(template) == 0:
            return [""]
        return list(self._sampler.generate_prompts(template, num_images))
