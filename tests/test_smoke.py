from __future__ import annotations

import dataclasses

import pytest
from dynamicprompts.parser.combinatorial_generator import CombinatorialGenerator
from dynamicprompts.parser.random_generator import RandomGenerator
from dynamicprompts.wildcardmanager import WildcardManager


@dataclasses.dataclass(frozen=True)
class SmokeTestCase:
    input: str
    must_generate: bool = True
    expected_combinatorial_count: int | None = None


test_cases = [
    SmokeTestCase(
        r"foo {0-1$$a|b|c|d}",
        must_generate=False,
        expected_combinatorial_count=5,
    ),
    SmokeTestCase(
        r"foo {a|b|c|d}",
        must_generate=True,
        expected_combinatorial_count=4,
    ),
]

gen_class = [
    CombinatorialGenerator,
    RandomGenerator,
]


@pytest.mark.parametrize("gen", gen_class)
@pytest.mark.parametrize("case", test_cases)
def test_generator(gen, case: SmokeTestCase, wildcard_manager: WildcardManager):
    generator = gen(wildcard_manager=wildcard_manager)
    gen_count = 0
    for result in generator.generate_prompts(
        case.input,
        num_prompts=(1 if gen is RandomGenerator else None),
    ):
        assert result
        gen_count += 1
    if case.must_generate:
        assert gen_count
    if case.expected_combinatorial_count is not None:
        if gen is CombinatorialGenerator:
            assert gen_count == case.expected_combinatorial_count
