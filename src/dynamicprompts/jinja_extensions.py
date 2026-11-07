from __future__ import annotations

import logging
import random
from itertools import permutations
from typing import Any, Callable, Iterable, TypeVar, cast

from jinja2 import Environment, pass_context, pass_environment
from jinja2.ext import Extension
from jinja2.nodes import CallBlock
from jinja2.parser import Parser
from jinja2.runtime import Context

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _rand(environment: Environment) -> random.Random:
    return cast(random.Random, environment.globals["rand"])


@pass_environment
def choice(environment: Environment, *items) -> Any:
    return _rand(environment).choice(items)


@pass_environment
def weighted_choice(environment: Environment, *items) -> Any:
    population, weights = zip(*items)
    return _rand(environment).choices(population, weights=weights)[0]


@pass_environment
def flip_coin(
    environment: Environment,
    first_result: Any = True,
    second_result: Any = False,
) -> Any:
    return _rand(environment).choice((first_result, second_result))


@pass_environment
def pick_multiple(
    environment: Environment,
    items: Iterable[T],
    return_length: int | None = None,
) -> list[T]:
    rand = _rand(environment)
    values = list(items)
    if not values or return_length == 0:
        return []
    if return_length is None:
        return_length = rand.randint(1, len(values))
    if return_length < 0:
        raise ValueError("return_length must not be negative")
    if return_length >= len(values):
        return values
    return rand.sample(values, return_length)


@pass_environment
def random_float(environment: Environment) -> float:
    return _rand(environment).random()


@pass_environment
def randint(environment: Environment, a: int, b: int) -> int:
    return _rand(environment).randint(a, b)


# A context filter, because Jinja folds environment filters on constant input
# at compile time, which would freeze the "random" result for every render.
@pass_context
def random_filter(context: Context, seq: Any) -> Any:
    try:
        return _rand(context.environment).choice(seq)
    except IndexError:
        return context.environment.undefined("No random item, sequence was empty.")


def permutation(
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


@pass_environment
def wildcard(environment: Environment, wildcard_name: str) -> list[str]:
    from dynamicprompts.generators import CombinatorialPromptGenerator
    from dynamicprompts.wildcards import WildcardManager

    wm = cast(WildcardManager, environment.globals["wildcard_manager"])
    generator = cast(
        CombinatorialPromptGenerator,
        environment.globals["generators"]["combinatorial"],  # type: ignore
    )

    return [str(r) for r in generator.generate(wm.to_wildcard(wildcard_name))]


@pass_environment
def random_sample(environment: Environment, prompt: str) -> str:
    generator = environment.globals["generators"]["random"]  # type: ignore

    ps = generator.generate(prompt, 1, seeds=[_rand(environment).randrange(2**32)])
    return str(next(iter(ps)))


@pass_environment
def combinatorial_sample(environment: Environment, prompt: str) -> list[str]:
    generator = environment.globals["generators"]["combinatorial"]  # type: ignore

    return [str(p) for p in generator.generate(prompt)]


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


DYNAMICPROMPTS_FUNCTIONS: dict[str, Any] = {
    "choice": choice,
    "weighted_choice": weighted_choice,
    "flip_coin": flip_coin,
    "pick_multiple": pick_multiple,
    "random": random_float,
    "randint": randint,
    "permutations": permutation,
    "wildcard": wildcard,
    "random_sample": random_sample,
    "all_combinations": combinatorial_sample,
}
