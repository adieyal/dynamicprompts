from __future__ import annotations

import dataclasses
import logging
from random import Random

from dynamicprompts import constants
from dynamicprompts.enums import SamplingMethod
from dynamicprompts.generators.promptgenerator import PromptGenerator
from dynamicprompts.parser.config import ParserConfig, default_parser_config
from dynamicprompts.parser.parse import parse
from dynamicprompts.samplers.count import (
    CombinationCount,
    ExactCount,
    combination_at,
    count_combinations,
)
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
        self._seed = seed
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

    def count(self, template: str | None) -> CombinationCount:
        """
        The number of prompts `generate` yields for `template` without a limit,
        computed without generating them. A random part (`{~a|b}`) counts as 1.
        """
        if not template:
            return ExactCount(0, False)
        command = parse(template, parser_config=self._context.parser_config)
        return count_combinations(command, self._context)

    def prompt_at(self, template: str, index: int) -> str:
        """
        The prompt `generate` yields at `index` for `template`, computed directly.
        Random parts are drawn from a generator seeded with (seed, index) when this
        generator has a seed, so the same seed and index give the same prompt.

        :raises IndexError: if `index` is not below `count(template)`.
        :raises ValueError: if the template contains a recursive wildcard.
        """
        if not template:
            raise IndexError(f"Prompt index {index} is out of range for 0 combinations")
        context = self._context
        if self._seed is not None:
            context = dataclasses.replace(context, rand=Random(f"{self._seed}:{index}"))
        command = parse(template, parser_config=context.parser_config)
        return combination_at(command, context, index)
