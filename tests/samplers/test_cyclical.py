import typing
from functools import partial

import pytest
from dynamicprompts.commands import (
    LiteralCommand,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.commands.base import SamplingMethod
from dynamicprompts.samplers.cycle import CyclicalSampler
from dynamicprompts.samplers.sampler_manager import ConcreteSamplerManager
from dynamicprompts.wildcardmanager import WildcardManager

NUM_CYCLES = 10


@pytest.fixture
def sampler_manager(wildcard_manager: WildcardManager) -> ConcreteSamplerManager:
    return ConcreteSamplerManager(
        wildcard_manager=wildcard_manager,
        default_sampling_method=SamplingMethod.CYCLICAL,
    )


@pytest.fixture
def sampler(sampler_manager: ConcreteSamplerManager) -> CyclicalSampler:
    return sampler_manager._samplers[SamplingMethod.CYCLICAL]


sequence_from_literals = partial(
    SequenceCommand.from_literals,
    sampling_method=SamplingMethod.CYCLICAL,
)
variants_from_literals_and_weights = partial(
    VariantCommand.from_literals_and_weights,
    sampling_method=SamplingMethod.CYCLICAL,
)
cyclical_literal = partial(LiteralCommand, sampling_method=SamplingMethod.CYCLICAL)
cyclical_sequence = partial(SequenceCommand, sampling_method=SamplingMethod.CYCLICAL)
cyclical_wildcard = partial(WildcardCommand, sampling_method=SamplingMethod.CYCLICAL)


def _test_expected(expected: list[str], gen: typing.Iterator[str]):
    for _ in range(NUM_CYCLES):
        for expected_prompt in expected:
            assert next(gen) == expected_prompt


class TestCyclicalGenerator:
    def test_variants_with_larger_bounds_than_choices(
        self,
        sampler_manager: ConcreteSamplerManager,
    ):
        template = "A red {3$$square|circle}"
        expected_prompts = [
            "A red square,circle",
            "A red circle,square",
            "A red square,circle",
            "A red circle,square",
            "A red square,circle",
        ]
        prompts = list(sampler_manager.sample_prompts(template, 5))

        assert prompts == expected_prompts

    def test_variants_with_pipe_separator(
        self,
        sampler: CyclicalSampler,
        sampler_manager: ConcreteSamplerManager,
    ):
        template = "A red {2$$|$$square|circle}"
        expected = ["A red square|circle", "A red circle|square"]
        assert list(sampler_manager.sample_prompts(template, 2)) == expected

    def test_nested_variants(self, sampler_manager: ConcreteSamplerManager):
        template = "A {red|green {square|circle}}"

        gen = list(sampler_manager.sample_prompts(template, 4))
        expected_prompts = [
            "A red",
            "A green square",
            "A red",
            "A green circle",
        ]
        assert list(gen) == expected_prompts
