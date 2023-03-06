from __future__ import annotations

import logging

from jinja2 import Environment
from jinja2.exceptions import TemplateSyntaxError

from dynamicprompts.generators.combinatorial import CombinatorialPromptGenerator
from dynamicprompts.generators.promptgenerator import (
    GeneratorException,
    PromptGenerator,
)
from dynamicprompts.generators.randomprompt import RandomPromptGenerator
from dynamicprompts.jinja_extensions import DYNAMICPROMPTS_FUNCTIONS, PromptExtension
from dynamicprompts.parser.config import ParserConfig, default_parser_config
from dynamicprompts.utils import squash_whitespace
from dynamicprompts.wildcardmanager import WildcardManager

logger = logging.getLogger(__name__)


class JinjaGenerator(PromptGenerator):
    def __init__(
        self,
        wildcard_manager: WildcardManager | None = None,
        context: dict | None = None,
        parser_config: ParserConfig = default_parser_config,
        unlink_seed_from_prompt: bool = False,
        ignore_whitespace: bool = False,
        limit_prompts=False,
    ) -> None:
        """
        Initialize a JinjaGenerator

        :param wildcard_manager: The wildcard manager to use for this generator, if None a null manager will be used
        :param context: The context to use for this generator, values in this dict will be available to the template
        :param parser_config: The parser config to use for this generator
        :param unlink_seed_from_prompt: Passed to the RandomPromptGenerator to allow random prompts even if the seed is fixed
        :param ignore_whitespace: Passed to the RandomPromptGenerator to ignore whitespace when generating prompts
        :param limit_prompts: Whether to limit the number of prompts generated to num_prompts, default is to generate num_prompts * num_prompts_in_template

        """

        self._wildcard_manager = wildcard_manager or WildcardManager()
        self._parser_config = parser_config
        self._unlink_seed_from_prompt = unlink_seed_from_prompt
        self._generators = {
            "random": RandomPromptGenerator(
                self._wildcard_manager,
                parser_config=self._parser_config,
                unlink_seed_from_prompt=self._unlink_seed_from_prompt,
                ignore_whitespace=ignore_whitespace,
            ),
            "combinatorial": CombinatorialPromptGenerator(
                self._wildcard_manager,
                parser_config=self._parser_config,
                ignore_whitespace=ignore_whitespace,
            ),
        }

        self._context = context or {}
        self._limit_prompts = limit_prompts
        self._ignore_whitespace = ignore_whitespace

    def generate(self, template: str, num_prompts: int = 1) -> list[str]:
        env = Environment(extensions=[PromptExtension])
        prompt_blocks: list[str] = []
        env.globals.update(
            {
                "wildcard_manager": self._wildcard_manager,
                "prompt_blocks": prompt_blocks,
                "parser_config": self._parser_config,
                "generators": self._generators,
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

        if self._limit_prompts:
            prompts = prompts[0:num_prompts]

        if self._ignore_whitespace:
            prompts = [squash_whitespace(p) for p in prompts]
        return prompts
