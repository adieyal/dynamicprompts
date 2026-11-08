from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import cast

from dynamicprompts.generators.combinatorial import CombinatorialPromptGenerator
from dynamicprompts.generators.promptgenerator import (
    GeneratorException,
    PromptGenerator,
)
from dynamicprompts.generators.randomprompt import RandomPromptGenerator
from dynamicprompts.parser.config import ParserConfig, default_parser_config
from dynamicprompts.utils import squash_whitespace
from dynamicprompts.wildcards import WildcardManager

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

    def _build_jinja_template(self, template: str):
        # Jinja2 and modules using it need to be late-imported here to work around issues
        # with incompatible versions of Jinja2 being installed in some downstream users' environments
        # (see https://github.com/adieyal/sd-dynamic-prompts/issues/476)
        import jinja2

        from dynamicprompts.jinja_extensions import (
            DYNAMICPROMPTS_FUNCTIONS,
            PromptExtension,
            random_filter,
        )

        # Templates in the wildcard folders can be imported or included.
        # A root mounted under a prefix is reached as "<prefix>/<template>".
        loaders: list[jinja2.BaseLoader] = []
        for prefix, items in self._wildcard_manager.root_map.items():
            folders = [item for item in items if isinstance(item, Path)]
            if not folders:
                continue
            folder_loader = jinja2.FileSystemLoader(folders)
            prefix = prefix.strip("/")
            loaders.append(
                jinja2.PrefixLoader({prefix: folder_loader})
                if prefix
                else folder_loader,
            )
        loader = jinja2.ChoiceLoader(loaders) if loaders else None
        env = jinja2.Environment(extensions=[PromptExtension], loader=loader)
        env.filters["random"] = random_filter
        prompt_blocks: list[str] = []
        env.globals.update(
            {
                "wildcard_manager": self._wildcard_manager,
                "prompt_blocks": prompt_blocks,
                "parser_config": self._parser_config,
                "generators": self._generators,
                "rand": random.Random(),
                **DYNAMICPROMPTS_FUNCTIONS,
            },
        )
        try:
            jinja_template = env.from_string(template)
        except jinja2.TemplateSyntaxError as e:
            logger.exception(e)
            raise GeneratorException(e.message) from e
        return jinja_template, prompt_blocks

    def generate(
        self,
        template: str,
        num_prompts: int = 1,
        *,
        seeds: list[int] | int | None = None,
        **kwargs,
    ) -> list[str]:
        if self._unlink_seed_from_prompt:
            seeds = None
        elif seeds:
            if isinstance(seeds, int):
                seeds = [seeds]

            if len(seeds) == 1:
                seeds = seeds * num_prompts

            if len(seeds) != num_prompts:
                raise ValueError(f"Expected {num_prompts} seeds, but got {len(seeds)}")

        jinja_template, prompt_blocks = self._build_jinja_template(template)
        rand = cast(random.Random, jinja_template.environment.globals["rand"])

        prompts = []
        for i in range(num_prompts):
            if seeds:
                rand.seed(seeds[i])
            prompts.append(jinja_template.render(**self._context))

        if prompt_blocks:  # May have been set by the templates being rendered
            prompts = prompt_blocks

        if self._limit_prompts:
            prompts = prompts[0:num_prompts]

        if self._ignore_whitespace:
            prompts = [squash_whitespace(p) for p in prompts]
        return prompts
