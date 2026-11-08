from __future__ import annotations

from collections import Counter
from random import Random

import pytest

from dynamicprompts.commands.base import SamplingMethod
from dynamicprompts.generators import CombinatorialPromptGenerator
from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.wildcards import WildcardManager
from dynamicprompts.wildcards.collection.list import ListWildcardCollection

LIMIT = 100


@pytest.fixture
def manager() -> WildcardManager:
    return WildcardManager.from_map(
        {
            "colors": ListWildcardCollection(["red", "blue", "red", "green"]),
            "random_line": ListWildcardCollection(["{~a|b}"]),
        },
    )


@pytest.fixture
def generator(manager: WildcardManager) -> CombinatorialPromptGenerator:
    return CombinatorialPromptGenerator(wildcard_manager=manager, seed=1)


def _all(generator: CombinatorialPromptGenerator, template: str) -> list[str]:
    prompts = generator.generate(template, max_prompts=LIMIT)
    assert len(prompts) < LIMIT, "the sampler did not end"
    return prompts


def test_duplicate_variant_options_are_kept(
    generator: CombinatorialPromptGenerator,
) -> None:
    assert _all(generator, "{a|a|b}") == ["a", "a", "b"]


def test_duplicate_options_are_distinct_in_tuples(
    generator: CombinatorialPromptGenerator,
) -> None:
    assert _all(generator, "{2$$a|a|b}") == ["a,a", "a,b", "a,a", "a,b", "b,a", "b,a"]


def test_cyclical_duplicate_options_are_distinct_in_tuples(
    manager: WildcardManager,
) -> None:
    context = SamplingContext(
        wildcard_manager=manager,
        default_sampling_method=SamplingMethod.CYCLICAL,
    )
    prompts = [str(p) for p in context.sample_prompts("{@2$$a|a|b}", 7)]
    assert prompts == ["a,a", "a,b", "a,a", "a,b", "b,a", "b,a", "a,a"]


def test_duplicate_wildcard_lines_are_kept(
    generator: CombinatorialPromptGenerator,
) -> None:
    assert _all(generator, "__colors__") == ["blue", "green", "red", "red"]


def test_random_draws_duplicate_lines_twice_as_often(manager: WildcardManager) -> None:
    context = SamplingContext(
        wildcard_manager=manager,
        default_sampling_method=SamplingMethod.RANDOM,
        rand=Random(0),
    )
    draws = Counter(str(p) for p in context.sample_prompts("__colors__", 4000))
    assert 0.45 < draws["red"] / 4000 < 0.55


@pytest.mark.parametrize(
    ("template", "expected"),
    [
        ("x __missing__", ["x __missing__"]),
        ("{__missing__|x}", ["__missing__", "x"]),
        ("{__missing__}", ["__missing__"]),
        ("a {__missing__}", ["a __missing__"]),
    ],
)
def test_missing_wildcard_yields_once(
    generator: CombinatorialPromptGenerator,
    template: str,
    expected: list[str],
) -> None:
    assert _all(generator, template) == expected


@pytest.mark.parametrize(
    "template",
    ["{~a|b}", "{@a|b}", "${v={~a|b}} ${v}", "__random_line__", "%{x...y$${~a|b}}"],
)
def test_lone_random_part_yields_once(
    generator: CombinatorialPromptGenerator,
    template: str,
) -> None:
    assert len(_all(generator, template)) == 1
