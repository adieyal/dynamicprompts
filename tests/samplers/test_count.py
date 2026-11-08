from __future__ import annotations

import re
import time
from pathlib import Path

import pytest

from dynamicprompts.generators import CombinatorialPromptGenerator
from dynamicprompts.parser.config import ParserConfig
from dynamicprompts.samplers.combinatorial import CombinatorialSampler
from dynamicprompts.samplers.count import ExactCount, UnboundedCount
from dynamicprompts.wildcards import WildcardManager
from dynamicprompts.wildcards.collection.list import ListWildcardCollection

COUNT_DATA_DIR = Path(__file__).parent.parent / "test_data" / "count"
# The oracle enumerates the sampler; a template reaching this many prompts is
# treated as endless.
ORACLE_LIMIT = 10_000

# (template, count) with no random parts: count == len(sampler output) and
# prompt_at(i) == sampler output[i] for every i.
EXACT_CASES = [
    ("{x|}{|x}", 4),
    ("{a|a|b}", 3),
    ("{a|{a|b}}", 3),
    ("{a {b|c}|d}", 3),
    ("{|}", 2),
    ("{2$$a|a|b}", 6),
    ("{3$$a|a|b}", 6),
    ("{4$$a|b}", 2),
    ("{1-3$$a|b|c}", 15),
    ("{0-1$$a|b}", 3),
    ("{2$$a|{b|c}}", 4),
    ("{2$$a {x|y}|b|c {p|q|r}}", 22),
    ("__mixed__", 6),
    ("__lines2__", 8),
    ("__colors__", 4),  # red, blue, red, green: duplicates count
    ("__w__", 4),  # YAML 3::heavy, light, 0.5::half
    ("__weighttxt__", 2),  # weights are not read from .txt files
    ("{__w__|z}", 5),
    ("__sub/*__", 2),
    ("__nested__", 5),
    ("__varline__", 2),
    ("{__mixed__}", 6),
    ("{2$$__colors__}", 12),
    ("{2$$__mixed__}", 16),
    ("{3$$__w__|z}", 8),
    ("__missing__ {a|b}", 2),
    ("{__missing__|x}", 2),
    ("{__missing__}", 1),
    ("a {__missing__}", 1),
    ("{2$$__missing__|x|y}", 6),
    ("${v={a|b}} ${v} ${v}", 4),
    ("${v=__colors__} ${v}-${v}", 16),
    ("${v=!{a|b}} ${v} ${v}", 1),
    ("${v=!__rec__} ${v}", 1),
    ("${v?=a} ${v}", 1),
    ("%{x...y$$__ab__}", 2),
    ("%{{x|z}...y$$__ab__}", 4),
    ("__zw__", 0),  # only a weight below 1
]

# (template, count) with random parts: each counts as 1.
RANDOM_CASES = [
    ("x {~a|b}", 1),
    ("{x|{~a|b}}", 2),
    ("{~a|b}", 1),
    ("__~colors__", 1),
    ("__rline2__", 1),
    ("${v={~a|b}} ${v}", 1),
    ("%{x...y$${~a|b}}", 1),
    ("{2$$a|{~p|q}|c}", 6),
    ("{~a|b} {x|y}", 2),
    ("{~__rec__|a}", 1),
]

# A regex for the random part's text in each RANDOM_CASES template.
RANDOM_PARTS = {
    "x {~a|b}": "[ab]",
    "{x|{~a|b}}": "[ab]",
    "{~a|b}": "[ab]",
    "__~colors__": "red|blue|green",
    "__rline2__": "[ab]",
    "${v={~a|b}} ${v}": "[ab]",
    "%{x...y$${~a|b}}": "[ab]",
    "{2$$a|{~p|q}|c}": "[pq]",
    "{~a|b} {x|y}": "[ab]",
    "{~__rec__|a}": "(loop )*end|a",
}

# Templates whose only non-combinatorial parts are cyclical: prompt_at(i) equals
# the sampler's i-th prompt, cyclical values included.
CYCLIC_CASES = [
    "{@a|b}",
    "{@a|b|c} {x|y|z}",
    "{@a|b} {@a|b} {x|y|z}",  # equal tokens share one generator
    "{@a|b} x {@a|b} {1|2|3}",
    "{@a|b} {x|y} {@p|q|r}",
    "{@a|b}{@c|d|e} {1|2|3|4|5|6}",
    "{x {@a|b|c} {1|2}|y} {p|q}",
    "{{@a|b}|y}",
    "{2$${@a|b|c}|x|y}",
    "{3$${@a|b}|x {1|2}|y}",
    "{@2$$a|a|b} {1|2|3|4|5|6|7}",
    "{@1-2$$a|b|c} {1|2|3|4|5|6|7|8|9|10}",
    "{@0-1$$a|b} {1|2|3|4}",
    "{@2$$a|b|{c|d}} {1|2|3|4|5|6|7|8|9}",
    "{@a|{b|c}} {1|2|3|4|5}",
    "{@{@a|b}|c} {1|2|3|4|5}",
    "{@x {a|b}|y} {1|2|3|4}",
    "__@ab__ {x|y|z}",
    "__@cline__ {1|2|3|4|5|6|7}",
    "__@missing__ {x|y}",
    "{@__ab__|z} {1|2|3|4|5}",
    "{@__cline__} {1|2|3|4|5|6|7}",
    "{__@ab__} {x|y}",
    "__cline__ {x|y}",
    "{2$$__cline__}",
    "{__cline__|z} {1|2|3}",
    "${v={@a|b}} ${v} ${v} {x|y}",
    "${v={@a|b|c} {1|2}} ${v} {x|y}",
    "${v=!{@a|b}} ${v} {x|y}",
    "${v={a|b}} {@${v}|c} {1|2|3|4|5}",
    "${v={@a|b|c}} {@${v} {x|y}|z} {1|2|3|4|5|6|7}",
    "%{x...y$${@a|b}} {1|2}",
    "%{{@p|q}...$$x {1|2|3}}",
    "%{w...$${@a|b} {1|2|3}}",
]

UNBOUNDED_CASES = [
    "__rec__",
    "{__rec__|x}",
    "a __rec__",
    "${v=__rec__} ${v}",
    "%{x...y$$__rec__}",
]


@pytest.fixture
def generator() -> CombinatorialPromptGenerator:
    return CombinatorialPromptGenerator(
        wildcard_manager=WildcardManager(COUNT_DATA_DIR),
        seed=42,
    )


def _sampled(generator: CombinatorialPromptGenerator, template: str) -> list[str]:
    prompts = generator.generate(template, max_prompts=ORACLE_LIMIT)
    assert len(prompts) < ORACLE_LIMIT, "the sampler did not end"
    return prompts


@pytest.mark.parametrize(("template", "expected"), EXACT_CASES)
def test_count_matches_sampler(
    generator: CombinatorialPromptGenerator,
    template: str,
    expected: int,
) -> None:
    assert generator.count(template) == ExactCount(expected, False)
    assert len(_sampled(generator, template)) == expected


@pytest.mark.parametrize(("template", "expected"), RANDOM_CASES)
def test_count_with_random_parts_matches_sampler(
    generator: CombinatorialPromptGenerator,
    template: str,
    expected: int,
) -> None:
    assert generator.count(template) == ExactCount(expected, True)
    assert len(_sampled(generator, template)) == expected


@pytest.mark.parametrize(("template", "expected"), EXACT_CASES)
def test_prompt_at_matches_sampler_order(
    generator: CombinatorialPromptGenerator,
    template: str,
    expected: int,
) -> None:
    prompts = _sampled(generator, template)
    assert [generator.prompt_at(template, i) for i in range(expected)] == prompts


@pytest.mark.parametrize("template", CYCLIC_CASES)
def test_prompt_at_matches_sampler_with_cyclical_parts(
    generator: CombinatorialPromptGenerator,
    template: str,
) -> None:
    prompts = _sampled(generator, template)
    count = generator.count(template)
    # `{__@ab__}` is enumerated and `${v=!...}` is a literal: no random parts.
    assert isinstance(count, ExactCount) and count.value == len(prompts)
    assert [generator.prompt_at(template, i) for i in range(count.value)] == prompts


@pytest.mark.parametrize(("template", "expected"), RANDOM_CASES)
def test_prompt_at_with_random_parts_matches_sampler_structure(
    generator: CombinatorialPromptGenerator,
    template: str,
    expected: int,
) -> None:
    def normalised(prompt: str) -> str:
        return re.sub(RANDOM_PARTS[template], "~", prompt)

    prompts = _sampled(generator, template)
    for i in range(expected):
        prompt = generator.prompt_at(template, i)
        again = CombinatorialPromptGenerator(
            wildcard_manager=WildcardManager(COUNT_DATA_DIR),
            seed=42,
        ).prompt_at(template, i)
        assert prompt == again
        assert normalised(prompt) == normalised(prompts[i])


@pytest.mark.parametrize(
    ("template", "options"),
    [
        ("  {a|b}   {x|y}  ", {}),
        ("__ab__   {@p|q}  {1|2}", {}),
        ("<a|b> <x|<p|q>>", {"variant_start": "<", "variant_end": ">"}),
        (
            "**ab** <@p|q> <1|2|3>",
            {"variant_start": "<", "variant_end": ">", "wildcard_wrap": "**"},
        ),
    ],
)
def test_prompt_at_honours_generator_options(
    template: str,
    options: dict[str, str],
) -> None:
    for ignore_whitespace in (False, True):
        generator = CombinatorialPromptGenerator(
            wildcard_manager=WildcardManager(COUNT_DATA_DIR),
            ignore_whitespace=ignore_whitespace,
            parser_config=ParserConfig(**options),
        )
        prompts = _sampled(generator, template)
        count = generator.count(template)
        assert isinstance(count, ExactCount) and count.value == len(prompts) > 1
        assert [generator.prompt_at(template, i) for i in range(count.value)] == prompts


@pytest.mark.parametrize("template", UNBOUNDED_CASES)
def test_recursive_wildcard_is_unbounded(
    generator: CombinatorialPromptGenerator,
    template: str,
) -> None:
    assert generator.count(template) == UnboundedCount()
    with pytest.raises(ValueError, match="recursive wildcard"):
        generator.prompt_at(template, 0)


def test_sampler_on_recursive_wildcard_raises(
    generator: CombinatorialPromptGenerator,
) -> None:
    with pytest.raises(RecursionError):
        generator.generate("__rec__", max_prompts=None)


@pytest.mark.parametrize("template", [None, ""])
def test_empty_template_counts_zero(
    generator: CombinatorialPromptGenerator,
    template: str | None,
) -> None:
    assert generator.count(template) == ExactCount(0, False)


@pytest.mark.parametrize(
    ("template", "index"),
    [("{a|b}", 2), ("{a|b}", -1), ("", 0), ("__colors__", 4), ("{2$$a|a|b}", 6)],
)
def test_prompt_at_out_of_range(
    generator: CombinatorialPromptGenerator,
    template: str,
    index: int,
) -> None:
    with pytest.raises(IndexError):
        generator.prompt_at(template, index)


def _manager(**wildcards: list[str]) -> WildcardManager:
    return WildcardManager.from_map(
        {name: ListWildcardCollection(lines) for name, lines in wildcards.items()},
    )


def test_two_wildcards_multiply() -> None:
    generator = CombinatorialPromptGenerator(
        wildcard_manager=_manager(
            characters=["knight", "wizard"],
            outfits=["armour", "robe", "cloak"],
        ),
    )
    assert generator.count("__characters__ __outfits__") == ExactCount(6, False)


def _five_wildcards(lines: int) -> tuple[WildcardManager, str]:
    names = "abcde"
    manager = _manager(
        **{n: [f"{n}{i:02d}" for i in range(lines)] for n in names},
    )
    return manager, " ".join(f"__{n}__" for n in names)


def test_count_does_not_enumerate(monkeypatch: pytest.MonkeyPatch) -> None:
    manager, template = _five_wildcards(10)

    def fail(*args: object) -> None:
        raise AssertionError("count enumerated prompts")

    for method in ("_get_sequence", "_get_variant", "_get_wildcard"):
        monkeypatch.setattr(CombinatorialSampler, method, fail)
    generator = CombinatorialPromptGenerator(wildcard_manager=manager)
    assert generator.count(template) == ExactCount(100_000, False)


def test_prompt_at_huge_index_is_direct() -> None:
    manager, template = _five_wildcards(100)
    generator = CombinatorialPromptGenerator(wildcard_manager=manager)
    assert generator.count(template) == ExactCount(10**10, False)

    start = time.monotonic()
    assert generator.prompt_at(template, 10**10 - 1) == "a99 b99 c99 d99 e99"
    assert generator.prompt_at(template, 1_234_567_890) == "a12 b34 c56 d78 e90"
    assert time.monotonic() - start < 5


def test_prompt_at_huge_index_with_cyclical_part_is_direct() -> None:
    manager, template = _five_wildcards(100)
    generator = CombinatorialPromptGenerator(wildcard_manager=manager)
    template = f"{{@a|b|c}} {template}"

    start = time.monotonic()
    # The cyclical part draws once per prompt: its value is the index modulo 3.
    assert generator.prompt_at(template, 10**10 - 1) == "a a99 b99 c99 d99 e99"
    assert generator.prompt_at(template, 1_234_567_891) == "b a12 b34 c56 d78 e91"
    assert time.monotonic() - start < 5
    # The same rule on a template small enough to enumerate.
    small = "{@a|b|c} __e__"
    assert generator.generate(small, None)[91] == generator.prompt_at(small, 91)
    assert generator.prompt_at(small, 91) == "b e91"


def test_prompt_at_with_random_parts_is_stable_per_seed_and_index() -> None:
    template = "{~a|b|c|d|e|f|g|h} {x|y}"

    def prompts(seed: int) -> list[str]:
        generator = CombinatorialPromptGenerator(seed=seed)
        return [generator.prompt_at(template, i) for i in range(2)]

    assert prompts(1) == prompts(1)
    # The combinatorial part follows the index; the random part is any option.
    for seed in range(5):
        first, second = prompts(seed)
        assert first[0] in "abcdefgh" and first.endswith(" x")
        assert second[0] in "abcdefgh" and second.endswith(" y")
    # Different seeds and indexes draw differently.
    assert len({p[0] for seed in range(20) for p in prompts(seed)}) > 1


def test_prompt_at_without_seed_returns_a_prompt() -> None:
    generator = CombinatorialPromptGenerator()
    assert generator.prompt_at("{~a|b} {x|y}", 1) in {"a y", "b y"}


def test_count_leaves_the_rng_untouched() -> None:
    template = "${v=!{~a|b|c|d|e|f}} ${v} {x|y|z}"
    expected = CombinatorialPromptGenerator(seed=5).generate(template, None)

    generator = CombinatorialPromptGenerator(seed=5)
    count = generator.count(template)
    assert isinstance(count, ExactCount) and count.value == 3
    assert generator.prompt_at(template, 0)
    assert generator.generate(template, None) == expected
