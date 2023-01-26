from __future__ import annotations

import logging
import random
from typing import Iterable, List, cast

from dynamicprompts.parser.commands import (
    Command,
    SequenceCommand,
)
from dynamicprompts.parser.parse import ActionBuilder, Parser
from dynamicprompts.utils import squash_whitespace
from dynamicprompts.wildcardmanager import WildcardManager

logger = logging.getLogger(__name__)


class RandomSequenceCommand(SequenceCommand):
    def __init__(self, tokens: list[Command] | None = None, separator=""):
        self._sep = separator
        super().__init__(tokens)

    def prompts(self) -> Iterable[str]:
        if len(self.tokens) == 0:
            return []
        else:
            partials = [p.get_prompt() for p in self.tokens]
            return [self._sep.join(partials)]


class RandomWildcardCommand(Command):
    def __init__(self, wildcard_manager, builder: ActionBuilder, token: str, rand=None):
        super().__init__(token)
        self._wildcard_manager = wildcard_manager
        self._wildcard = token[0]
        self._builder = builder
        self._random = rand or random

    def prompts(self) -> Iterable[str]:
        generator = self._builder.create_generator()
        values = self._wildcard_manager.get_all_values(self._wildcard)
        if len(values) == 0:
            logger.warning(f"No values found for wildcard {self._wildcard}")
            return [f"__{self._wildcard}__"]
        val = self._random.choice(values)
        prompts = generator.generate_prompts(val, 1)

        return prompts

    def __repr__(self):
        return f"{self.__class__.__name__}({self._wildcard!r})"


class RandomVariantCommand(Command):
    def __init__(self, variants, min_bound=1, max_bound=1, sep=",", rand=None):
        super().__init__(variants)
        self._weights = [p["weight"][0] for p in variants]
        self._values = [p["val"] for p in variants]
        self.min_bound = min_bound
        self.max_bound = max_bound
        self.sep = sep
        self._remaining_values = self._values
        self._random = rand or random

    def _combo_to_prompt(self, combo: list[SequenceCommand]) -> Iterable[list[str]]:
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

        num_choices = self._random.randint(self.min_bound, self.max_bound)
        combo = self._random.choices(self._values, weights=self._weights, k=num_choices)
        for prompt_arr in self._combo_to_prompt(combo):
            yield self.sep.join(prompt_arr)

    def __repr__(self):
        z = zip(self._weights, self._values)
        return f"{self.__class__.__name__}({list(z)!r})"


class RandomActionBuilder(ActionBuilder):
    def __init__(
        self,
        wildcard_manager: WildcardManager,
        rand=None,
        seq_sep="",
        ignore_whitespace=False,
    ):
        super().__init__(wildcard_manager, ignore_whitespace=ignore_whitespace)
        self._seq_sep = seq_sep
        self._random = rand or random

    def create_variant_command(self, variants, min_bound=1, max_bound=1, sep=","):
        return RandomVariantCommand(
            variants,
            min_bound,
            max_bound,
            sep,
            rand=self._random,
        )

    def create_wildcard_command(self, token: str):
        return RandomWildcardCommand(
            self._wildcard_manager,
            self,
            token,
            rand=self._random,
        )

    def create_sequence_command(self, token_list: list[Command]):
        return RandomSequenceCommand(token_list, separator=self._seq_sep)

    def create_generator(self):
        return RandomGenerator(
            self._wildcard_manager,
            ignore_whitespace=self._ignore_whitespace,
        )


class RandomGenerator:
    def __init__(
        self,
        wildcard_manager: WildcardManager,
        rand=None,
        ignore_whitespace=False,
    ):
        if rand is None:
            self._random = random
        else:
            self._random = rand
        self._wildcard_manager = wildcard_manager
        self._ignore_whitespace = ignore_whitespace

    def get_action_builder(self) -> ActionBuilder:
        return RandomActionBuilder(
            self._wildcard_manager,
            seq_sep="",
            ignore_whitespace=self._ignore_whitespace,
            rand=self._random,
        )

    def configure_parser(self):
        builder = self.get_action_builder()
        parser = Parser(builder)

        return parser.prompt

    def generate_prompts(self, prompt: str, num_prompts: int = 0) -> list[str]:
        if len(prompt) == 0:
            return []

        parser = self.configure_parser()
        tokens = parser.parse_string(prompt)
        tokens = cast(List[Command], tokens)

        generated_prompts = []
        if len(tokens) == 0:
            return []

        for i in range(num_prompts):

            prompts = list(tokens[0].prompts())
            if len(prompts) == 0:

                continue
            if self._ignore_whitespace:
                prompt = squash_whitespace(prompts[0])
            else:
                prompt = prompts[0]

            generated_prompts.append(prompt)

        return generated_prompts
