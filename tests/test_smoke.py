from __future__ import annotations

import dataclasses

import pytest
from dynamicprompts.samplers import CombinatorialSampler, RandomSampler, Sampler
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


@pytest.mark.parametrize("sampler_class", [CombinatorialSampler, RandomSampler])
@pytest.mark.parametrize("case", test_cases)
def test_generator(
    sampler_class: type[Sampler],
    case: SmokeTestCase,
    wildcard_manager: WildcardManager,
) -> None:
    sampler = sampler_class(wildcard_manager=wildcard_manager)
    gen_count = 0
    for result in sampler.generate_prompts(
        case.input,
        num_prompts=(1 if sampler_class is RandomSampler else None),
    ):
        assert result
        gen_count += 1
    if case.must_generate:
        assert gen_count
    if case.expected_combinatorial_count is not None:
        if sampler_class is CombinatorialSampler:
            assert gen_count == case.expected_combinatorial_count
