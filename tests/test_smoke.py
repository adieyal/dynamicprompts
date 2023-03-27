from __future__ import annotations

import dataclasses

import pytest
from dynamicprompts.enums import SamplingMethod
from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.wildcards import WildcardManager


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


@pytest.mark.parametrize(
    "sampling_method",
    [SamplingMethod.COMBINATORIAL, SamplingMethod.RANDOM],
)
@pytest.mark.parametrize("case", test_cases)
def test_generator(
    sampling_method: SamplingMethod,
    case: SmokeTestCase,
    wildcard_manager: WildcardManager,
) -> None:
    context = SamplingContext(
        wildcard_manager=wildcard_manager,
        default_sampling_method=sampling_method,
    )
    gen_count = 0
    max_count = 10

    for result in context.sample_prompts(
        case.input,
        num_prompts=max_count,
    ):
        assert result
        gen_count += 1
    if case.must_generate:
        assert gen_count
    if case.expected_combinatorial_count is not None:
        if sampling_method is SamplingMethod.COMBINATORIAL:
            assert gen_count == case.expected_combinatorial_count
