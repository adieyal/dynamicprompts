from __future__ import annotations

import logging
from typing import Iterable

from dynamicprompts import constants
from dynamicprompts.enums import SamplingMethod
from dynamicprompts.generators.promptgenerator import PromptGenerator
from dynamicprompts.parser.config import ParserConfig, default_parser_config
from dynamicprompts.sampler_routers import ConcreteSamplerRouter
from dynamicprompts.wildcardmanager import WildcardManager

logger = logging.getLogger(__name__)


class CombinatorialPromptGenerator(PromptGenerator):
    def __init__(
        self,
        wildcard_manager: WildcardManager,
        ignore_whitespace: bool = False,
        parser_config: ParserConfig = default_parser_config,
    ) -> None:
        self._wildcard_manager = wildcard_manager
        self._router = ConcreteSamplerRouter(
            wildcard_manager=wildcard_manager,
            default_sampling_method=SamplingMethod.COMBINATORIAL,
            ignore_whitespace=ignore_whitespace,
            parser_config=parser_config,
        )

    def generate(  # type: ignore[override]
        self,
        template: str | None,
        max_prompts: int | None = constants.MAX_IMAGES,
    ) -> Iterable[str]:
        if template is None or len(template) == 0:
            return [""]
        prompts = self._router.sample_prompts(template, max_prompts)

        return prompts
