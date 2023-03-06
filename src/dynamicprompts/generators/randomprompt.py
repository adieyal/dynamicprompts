from __future__ import annotations

import logging
from random import Random

from dynamicprompts.commands.base import SamplingMethod
from dynamicprompts.constants import DEFAULT_RANDOM
from dynamicprompts.generators.promptgenerator import PromptGenerator
from dynamicprompts.parser.config import ParserConfig, default_parser_config
from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.wildcardmanager import WildcardManager

logger = logging.getLogger(__name__)


def _get_random(*, seed: int | None, unlink_seed_from_prompt: bool) -> Random:
    if unlink_seed_from_prompt:
        return DEFAULT_RANDOM
    rand = Random()
    if seed is not None:
        rand.seed(seed)
    return rand


class RandomPromptGenerator(PromptGenerator):
    def __init__(
        self,
        wildcard_manager: WildcardManager | None = None,
        seed: int | None = None,
        unlink_seed_from_prompt: bool = False,
        ignore_whitespace: bool = False,
        parser_config: ParserConfig = default_parser_config,
    ) -> None:
        wildcard_manager = wildcard_manager or WildcardManager()
        self._context = SamplingContext(
            wildcard_manager=wildcard_manager,
            default_sampling_method=SamplingMethod.RANDOM,
            ignore_whitespace=ignore_whitespace,
            parser_config=parser_config,
            rand=_get_random(
                seed=seed,
                unlink_seed_from_prompt=unlink_seed_from_prompt,
            ),
        )

    def generate(self, template: str | None, num_images: int = 1) -> list[str]:
        return list(self._context.sample_prompts((template or ""), num_images))
