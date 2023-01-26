from __future__ import annotations

from collections import OrderedDict
from itertools import islice
from typing import Iterable

from dynamicprompts.parser.commands import (
    Command,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.parser.parse import (
    ActionBuilder,
    Parser,
)
from dynamicprompts.utils import squash_whitespace
from dynamicprompts.wildcardmanager import WildcardManager


class CombinatorialSequenceCommand(SequenceCommand):
    def __init__(
        self,
        tokens: list[Command] | None = None,
        separator="",
    ):
        self._sep = separator
        super().__init__(tokens)

    def prompts(self, tokens: list[Command] | None = None) -> Iterable[str]:
        if tokens is None:
            tokens = self.tokens

        if len(tokens) == 0:
            yield ""
        else:
            token = tokens[0]
            for prompt in token.prompts():
                for next_prompts in self.prompts(tokens[1:]):
                    res = prompt + self._sep + next_prompts
                    yield res


class CombinatorialWildcardCommand(WildcardCommand):
    def __init__(
        self,
        wildcard_manager: WildcardManager,
        builder: ActionBuilder,
        token,
    ):
        super().__init__(wildcard_manager, token)
        self._wildcard_manager = wildcard_manager
        self._wildcard = token[0]
        self._builder = builder

    def prompts(self) -> Iterable[str]:
        generator = self._builder.create_generator()
        values = self._wildcard_manager.get_all_values(self._wildcard)
        for val in values:
            for prompt in generator.generate_prompts(val):
                yield prompt

    def __repr__(self):
        return f"{self.__class__.__name__}({self._wildcard!r})"


class CombinatorialVariantCommand(VariantCommand):
    def _combo_to_prompt(self, combo: list[SequenceCommand]) -> Iterable[list[str]]:
        if len(combo) == 0:
            yield []
        else:
            c_1, c_rest = combo[0], combo[1:]

            for p in c_1.prompts():
                for rest_prompt in self._combo_to_prompt(c_rest):
                    if rest_prompt != []:
                        yield [p] + rest_prompt
                    else:
                        yield [p]

    def _dedupe(self, arr: list[str]) -> tuple[str]:
        d = OrderedDict()
        for item in arr:
            d[item] = None
        return tuple(d.keys())

    def prompts(self) -> Iterable[str]:
        if len(self._values) == 0:
            return []

        seen = set()

        for bound in range(self.min_bound, self.max_bound + 1):
            for combo in self._combinations(bound):
                for prompt_arr in self._combo_to_prompt(combo):
                    deduped_arr = self._dedupe(prompt_arr)
                    correct_size = len(deduped_arr) == bound
                    if deduped_arr not in seen and correct_size:
                        seen.add(deduped_arr)
                        yield self.sep.join(deduped_arr)

    def __repr__(self):
        z = zip(self._weights, self._values)
        return f"{self.__class__.__name__}({list(z)!r})"


class CombinatorialActionBuilder(ActionBuilder):
    def create_variant_command(self, variants, min_bound=1, max_bound=1, sep=","):
        return CombinatorialVariantCommand(variants, min_bound, max_bound, sep)

    def create_wildcard_command(self, token: str):
        return CombinatorialWildcardCommand(self._wildcard_manager, self, token)

    def create_sequence_command(self, token_list: list[Command]):
        return CombinatorialSequenceCommand(token_list)

    def create_generator(self):
        return CombinatorialGenerator(
            self._wildcard_manager,
            ignore_whitespace=self._ignore_whitespace,
        )


class CombinatorialGenerator:
    def __init__(self, wildcard_manager, ignore_whitespace=False):
        self._wildcard_manager = wildcard_manager
        self._ignore_whitespace = ignore_whitespace

    def get_action_builder(self) -> ActionBuilder:
        return CombinatorialActionBuilder(
            self._wildcard_manager,
            self._ignore_whitespace,
        )

    def configure_parser(self) -> Parser:
        builder = self.get_action_builder()
        parser = Parser(builder)

        return parser

    def generate_prompts(
        self,
        prompt: str,
        num_prompts: int | None = None,
    ) -> Iterable[str]:
        if len(prompt) == 0:
            return []

        parser = self.configure_parser()
        sequence = parser.parse(prompt)
        prompts = sequence.prompts()

        if self._ignore_whitespace:
            prompts = (squash_whitespace(p) for p in prompts)

        if num_prompts is None:
            return prompts
        else:
            return islice(prompts, num_prompts)
