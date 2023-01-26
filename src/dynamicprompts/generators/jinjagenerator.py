from __future__ import annotations

import logging
import random
import re
from itertools import permutations
from typing import Any, Callable, Iterable, cast

from jinja2 import Environment
from jinja2.exceptions import TemplateSyntaxError
from jinja2.ext import Extension
from jinja2.nodes import CallBlock
from jinja2.parser import Parser

from dynamicprompts.generators.promptgenerator import (
    GeneratorException,
    PromptGenerator,
)
from dynamicprompts.wildcardmanager import WildcardManager

logger = logging.getLogger(__name__)

re_wildcard = re.compile(r"__(.*?)__")
re_combinations = re.compile(r"\{([^{}]*)}")


class RandomExtension(Extension):
    def __init__(self, environment: Environment) -> None:
        super().__init__(environment)
        environment.globals["choice"] = self.choice
        environment.globals["weighted_choice"] = self.weighted_choice
        environment.globals["random"] = self.random
        environment.globals["randint"] = self.randint

    def choice(self, *items) -> Any:
        return random.choice(items)

    def weighted_choice(self, *items) -> Any:
        population, weights = zip(*items)
        return random.choices(population, weights=weights)[0]

    def random(self) -> float:
        return random.random()

    def randint(self, low: int, high: int) -> int:
        return random.randint(low, high)


class PermutationExtension(Extension):
    def __init__(self, environment: Environment) -> None:
        super().__init__(environment)
        environment.globals["permutations"] = self.permutation

    def permutation(
        self,
        items: Iterable[Any],
        low: int,
        high: int | None = None,
    ) -> list[Any]:
        vars: list[Any] = []
        if high is None:
            high = low

        for i in range(low, high + 1):
            vars.extend(permutations(items, i))

        return vars


class WildcardExtension(Extension):
    def __init__(self, environment: Environment) -> None:
        super().__init__(environment)
        environment.globals["wildcard"] = self.wildcard

    def wildcard(self, wildcard_name: str) -> list[str]:
        wm = cast(WildcardManager, self.environment.globals["wildcard_manager"])
        values = []

        for value in wm.get_all_values(wildcard_name):
            if re_wildcard.fullmatch(value):
                values.extend(self.wildcard(value))
            elif re_combinations.fullmatch(value):
                val = re_combinations.findall(value)[0]
                options = val.split("|")
                choice_ext = RandomExtension(self.environment)
                values.append(choice_ext.choice(options))
            else:
                values.append(value)
        return values


class PromptExtension(Extension):
    tags = {"prompt"}

    def __init__(self, environment: Environment) -> None:
        super().__init__(environment)
        environment.extend(prompt_blocks=[])

    def parse(self, parser: Parser) -> CallBlock:
        lineno = next(parser.stream).lineno
        body = parser.parse_statements(
            ("name:endprompt",),
            drop_needle=True,
        )
        node = CallBlock(
            self.call_method("_prompt", []),
            [],
            [],
            body,
        )
        node.set_lineno(lineno)
        return node

    def _prompt(self, caller: Callable) -> Any:
        value = caller()
        prompt_blocks = cast(list, self.environment.globals["prompt_blocks"])
        prompt_blocks.append(value)
        return value


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
        env = Environment(
            extensions=[
                RandomExtension,
                PromptExtension,
                WildcardExtension,
                PermutationExtension,
            ],
        )
        prompt_blocks: list[str] = []
        env.globals.update(
            {
                "wildcard_manager": self._wildcard_manager,
                "prompt_blocks": prompt_blocks,
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
