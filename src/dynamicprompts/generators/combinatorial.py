from __future__ import annotations

import logging
from random import Random

from dynamicprompts import constants
from dynamicprompts.enums import SamplingMethod
from dynamicprompts.generators.promptgenerator import PromptGenerator
from dynamicprompts.parser.config import ParserConfig, default_parser_config
from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.wildcards import WildcardManager

logger = logging.getLogger(__name__)


class CombinatorialPromptGenerator(PromptGenerator):
    def __init__(
        self,
        wildcard_manager: WildcardManager | None = None,
        ignore_whitespace: bool = False,
        parser_config: ParserConfig = default_parser_config,
        seed: int | None = None,
    ) -> None:
        """
        :param seed: Seeds random choices inside the template (such as `{~a|b}`),
            so the same seed gives the same prompts. Without it they use the shared generator.
        """
        wildcard_manager = wildcard_manager or WildcardManager()
        self._context = SamplingContext(
            wildcard_manager=wildcard_manager,
            default_sampling_method=SamplingMethod.COMBINATORIAL,
            ignore_whitespace=ignore_whitespace,
            parser_config=parser_config,
            rand=constants.DEFAULT_RANDOM if seed is None else Random(seed),
        )

    def generate(
        self,
        template: str | None,
        max_prompts: int | None = constants.MAX_IMAGES,
        **kwargs,
    ) -> list[str]:
        return [
            str(p) for p in self._context.sample_prompts((template or ""), max_prompts)
        ]
