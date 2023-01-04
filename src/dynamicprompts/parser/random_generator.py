from __future__ import annotations

import logging
import random
from typing import cast, Iterable, List

from .parse import Parser, ActionBuilder
from .commands import (
    SequenceCommand,
    Command,
)
from dynamicprompts.wildcardmanager import WildcardManager

logger = logging.getLogger(__name__)


class RandomSequenceCommand(SequenceCommand):
    def __init__(self, tokens: List[Command] | None = None, separator=" "):
        self._sep = separator
        super().__init__(tokens)

    def prompts(self) -> Iterable[str]:
        if len(self.tokens) == 0:
            return []
        else:
            partials = [p.get_prompt() for p in self.tokens]
            return [self._sep.join(partials)]


class RandomWildcardCommand(Command):
    def __init__(self, wildcard_manager, token: str):
        super().__init__(token)
        self._wildcard_manager = wildcard_manager
        self._wildcard = token[0]

    def prompts(self) -> Iterable[str]:
        generator = RandomGenerator(self._wildcard_manager)
        values = self._wildcard_manager.get_all_values(self._wildcard)
        if len(values) == 0:
            logger.warning(f"No values found for wildcard {self._wildcard}")
            return [f"__{self._wildcard}__"]
        val = random.choice(values)
        prompts = generator.generate_prompts(val, 1)

        return prompts

    def __repr__(self):
        return f"{self.__class__.__name__}({self._wildcard!r})"


class RandomVariantCommand(Command):
    def __init__(self, variants, min_bound=1, max_bound=1, sep=","):
        super().__init__(variants)
        self._weights = [p["weight"][0] for p in variants]
        self._values = [p["val"] for p in variants]
        self.min_bound = min_bound
        self.max_bound = max_bound
        self.sep = sep
        self._remaining_values = self._values

    def _combo_to_prompt(self, combo: List[SequenceCommand]) -> Iterable[List[str]]:
        if len(combo) == 0:
            yield []
        else:
            c_1, c_rest = combo[0], combo[1:]

            for p in c_1.prompts():
                for rest_prompt in self._combo_to_prompt(c_rest):
                    if rest_prompt != "":
                        yield [p] + rest_prompt
                    else:
                        yield [p]

    def prompts(self) -> Iterable[str]:
        if len(self._values) == 0:
            return []

        num_choices = random.randint(self.min_bound, self.max_bound)
        combo = random.choices(self._values, weights=self._weights, k=num_choices)
        for prompt_arr in self._combo_to_prompt(combo):
            yield self.sep.join(prompt_arr)

    def __repr__(self):
        z = zip(self._weights, self._values)
        return f"{self.__class__.__name__}({list(z)!r})"


class RandomActionBuilder(ActionBuilder):
    def create_variant_command(self, variants, min_bound=1, max_bound=1, sep=","):
        return RandomVariantCommand(variants, min_bound, max_bound, sep)

    def create_wildcard_command(self, token: str):
        return RandomWildcardCommand(self._wildcard_manager, token)

    def create_sequence_command(self, token_list: List[Command]):
        return RandomSequenceCommand(token_list)


class RandomGenerator:
    def __init__(self, wildcard_manager: WildcardManager, rand=None):
        if rand is None:
            self._random = random
        else:
            self._random = rand
        self._wildcard_manager = wildcard_manager

    def get_action_builder(self) -> ActionBuilder:
        return RandomActionBuilder(self._wildcard_manager)

    def configure_parser(self):
        builder = self.get_action_builder()
        parser = Parser(builder)

        return parser.prompt

    def generate_prompts(self, prompt: str, num_prompts: int) -> List[str]:
        if len(prompt) == 0:
            return []

        parser = self.configure_parser()
        tokens = parser.parse_string(prompt)
        tokens = cast(List[Command], tokens)

        squash_whitespace = lambda s: " ".join(s.split())

        generated_prompts = []
        for i in range(num_prompts):
            prompts = list(tokens[0].prompts())
            generated_prompts.append(squash_whitespace(prompts[0]))

        return generated_prompts
