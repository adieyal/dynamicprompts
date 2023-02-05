from __future__ import annotations

import logging

from jinja2 import Environment
from jinja2.exceptions import TemplateSyntaxError

from dynamicprompts.generators.promptgenerator import (
    GeneratorException,
    PromptGenerator,
)
from dynamicprompts.jinja_extensions import DYNAMICPROMPTS_FUNCTIONS, PromptExtension
from dynamicprompts.wildcardmanager import WildcardManager

logger = logging.getLogger(__name__)


class JinjaGenerator(PromptGenerator):
    def __init__(
        self,
        wildcard_manager: WildcardManager | None = None,
        context: dict | None = None,
    ) -> None:
        self._wildcard_manager = wildcard_manager

        if context is not None:
            self._context = context
        else:
            self._context = {}

    def generate(self, template: str, num_prompts: int = 1) -> list[str]:
        env = Environment(extensions=[PromptExtension])
        prompt_blocks: list[str] = []
        env.globals.update(
            {
                "wildcard_manager": self._wildcard_manager,
                "prompt_blocks": prompt_blocks,
                **DYNAMICPROMPTS_FUNCTIONS,
            },
        )

        try:
            jinja_template = env.from_string(template)
        except TemplateSyntaxError as e:
            logger.exception(e)
            raise GeneratorException(e.message) from e

        prompts = []
        for i in range(num_prompts):
            s = jinja_template.render(**self._context)
            prompts.append(s)

        if prompt_blocks:
            prompts = prompt_blocks
        return prompts
