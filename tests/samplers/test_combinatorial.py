from __future__ import annotations

from unittest import mock

import pytest
from dynamicprompts.commands import (
    SamplingMethod,
)
from dynamicprompts.samplers.combinatorial import CombinatorialSampler
from dynamicprompts.samplers.sampler_manager import ConcreteSamplerManager
from dynamicprompts.wildcardmanager import WildcardManager

from tests.consts import RED_GREEN_BLUE


@pytest.fixture
def sampler_manager(wildcard_manager: WildcardManager):

    with mock.patch.object(
        wildcard_manager,
        "get_all_values",
        return_value=RED_GREEN_BLUE,
    ):

        yield ConcreteSamplerManager(
            wildcard_manager=wildcard_manager,
            default_sampling_method=SamplingMethod.COMBINATORIAL,
        )


@pytest.fixture
def sampler(sampler_manager: ConcreteSamplerManager) -> CombinatorialSampler:
    return sampler_manager._samplers[SamplingMethod.COMBINATORIAL]


class TestGenerator:
    def test_empty(self, sampler_manager: ConcreteSamplerManager):
        prompts = sampler_manager.sample_prompts("", 5)
        assert list(prompts) == []

    def test_literals(self, sampler_manager: ConcreteSamplerManager):
        prompts = list(sampler_manager.sample_prompts("A literal sentence", 5))
        assert prompts == ["A literal sentence"]

    def test_literal_with_square_brackets(
        self,
        sampler_manager: ConcreteSamplerManager,
    ):
        prompts = list(sampler_manager.sample_prompts("Test [low emphasis]", 1))
        assert prompts == ["Test [low emphasis]"]

    def test_variants(self, sampler_manager: ConcreteSamplerManager):
        prompts = list(sampler_manager.sample_prompts("A red {square|circle}", 5))
        assert prompts == ["A red square", "A red circle"]

    def test_variant_with_blank(self, sampler_manager: ConcreteSamplerManager):
        prompts = list(sampler_manager.sample_prompts("A {|red|blue} rose", 3))
        assert prompts == ["A  rose", "A red rose", "A blue rose"]

    def test_two_variants(self, sampler_manager: ConcreteSamplerManager):
        prompts = list(
            sampler_manager.sample_prompts("A {red|green} {square|circle}", 5),
        )
        assert prompts == [
            "A red square",
            "A red circle",
            "A green square",
            "A green circle",
        ]

        prompts = list(
            sampler_manager.sample_prompts("A {red|green} {square|circle}", 2),
        )
        assert prompts == ["A red square", "A red circle"]

    def test_combination_variants(self, sampler_manager: ConcreteSamplerManager):
        prompts = list(
            sampler_manager.sample_prompts("A {2$$red|green|blue} square", 10),
        )
        assert prompts == [
            "A red,green square",
            "A red,blue square",
            "A green,red square",
            "A green,blue square",
            "A blue,red square",
            "A blue,green square",
        ]

    def test_combination_variants_range(self, sampler_manager: ConcreteSamplerManager):
        prompts = list(
            sampler_manager.sample_prompts("A {1-2$$red|green|blue} square", 10),
        )
        assert prompts == [
            "A red square",
            "A green square",
            "A blue square",
            "A red,green square",
            "A red,blue square",
            "A green,red square",
            "A green,blue square",
            "A blue,red square",
            "A blue,green square",
        ]

    def test_combination_variants_with_separator(
        self,
        sampler_manager: ConcreteSamplerManager,
    ):
        prompts = list(
            sampler_manager.sample_prompts("A {2$$ and $$red|green|blue} square", 10),
        )
        assert prompts == [
            "A red and green square",
            "A red and blue square",
            "A green and red square",
            "A green and blue square",
            "A blue and red square",
            "A blue and green square",
        ]

    # def test_variants_with_larger_range_than_choices(
    #     self,
    #     sampler_manager: ConcreteSamplerManager,
    # ):
    #     shapes = ["square", "circle"]
    #     with mock.patch(
    #         "dynamicprompts.samplers.random.DEFAULT_RANDOM",
    #     ) as mock_random:
    #         mock_random.randint.return_value = 3
    #         mock_random.choices.side_effect = [shapes]
    #         prompts = list(sampler_manager.sample_prompts("A red {3$$square|circle}", 1))

    #         assert len(prompts) == 0

    def test_wildcards(self, sampler_manager: ConcreteSamplerManager):
        prompts = list(
            sampler_manager.sample_prompts("A __colours__ {square|circle}", 6),
        )

        assert prompts == [
            "A red square",
            "A red circle",
            "A green square",
            "A green circle",
            "A blue square",
            "A blue circle",
        ]

        sampler_manager._wildcard_manager.get_all_values.assert_called_once_with(
            "colours",
        )

    def test_nested_wildcard(self, sampler_manager: ConcreteSamplerManager):
        prompts = list(sampler_manager.sample_prompts("{__colours__}", 6))
        assert prompts == RED_GREEN_BLUE

    def test_nested_wildcard_with_range(self, sampler_manager: ConcreteSamplerManager):
        prompts = list(sampler_manager.sample_prompts("{2$$__colours__}", 6))
        assert prompts == RED_GREEN_BLUE

    def test_nested_wildcard_with_range_and_literal(
        self,
        sampler_manager: ConcreteSamplerManager,
    ):

        prompts = list(sampler_manager.sample_prompts("{2$$__colours__|black}", 20))
        assert prompts == [
            "red,black",
            "green,black",
            "blue,black",
            "black,red",
            "black,green",
            "black,blue",
        ]
