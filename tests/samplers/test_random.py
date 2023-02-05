from typing import cast
from unittest import mock

import pytest
from dynamicprompts.commands import (
    LiteralCommand,
    SamplingMethod,
    SequenceCommand,
    WildcardCommand,
)
from dynamicprompts.samplers.random import RandomSampler
from dynamicprompts.samplers.sampler_manager import ConcreteSamplerManager
from dynamicprompts.wildcardmanager import WildcardManager

from tests.consts import RED_AND_GREEN, RED_GREEN_BLUE


@pytest.fixture
def sampler_manager(wildcard_manager: WildcardManager) -> ConcreteSamplerManager:
    return ConcreteSamplerManager(
        wildcard_manager=wildcard_manager,
        default_sampling_method=SamplingMethod.RANDOM,
    )


@pytest.fixture
def sampler(sampler_manager: ConcreteSamplerManager) -> RandomSampler:
    return cast(RandomSampler, sampler_manager._samplers[SamplingMethod.RANDOM])

    # def test_combinatorial_sampling_method(self, sampler_manager: ConcreteSamplerManager):
    #     command = VariantCommand.from_literals_and_weights(
    #         ONE_TWO_THREE,
    #         sampling_method=SamplingMethod.COMBINATORIAL,
    #     )
    #     prompts = list(sampler_manager.sample_prompts(command, 3))
    #     assert prompts == ONE_TWO_THREE

    #     def test_combinatorial_sampling_method_with_sequence(self, sampler: RandomSampler):
    #         command = SequenceCommand(
    #             [
    #                 LiteralCommand("XXX"),
    #                 VariantCommand.from_literals_and_weights(
    #                     ONE_TWO_THREE,
    #                     sampling_method=SamplingMethod.COMBINATORIAL,
    #                 ),
    #             ],
    #         )

    #         prompts = list(sampler.generate_prompts(command, 5))
    #         assert prompts == ["XXXone", "XXXtwo", "XXXthree", "XXXone", "XXXtwo"]

    #     def test_random_sampling_method(self, sampler: RandomSampler):
    #         command = VariantCommand.from_literals_and_weights(
    #             ONE_TWO_THREE,
    #             sampling_method=SamplingMethod.RANDOM,
    #         )

    #         with mock.patch.object(sampler._random, "choices") as mock_choices:
    #             random_choices = [
    #                 [LiteralCommand("one")],
    #                 [LiteralCommand("three")],
    #                 [LiteralCommand("two")],
    #                 [LiteralCommand("one")],
    #             ]
    #             mock_choices.side_effect = random_choices

    #             for c in random_choices:
    #                 prompt = next(sampler.generator_from_command(command))
    #                 assert prompt == c[0].literal


class TestWildcardsCommand:
    def test_combinatorial_sampling_method(self, sampler: RandomSampler):
        command = WildcardCommand(
            "colors",
            sampling_method=SamplingMethod.COMBINATORIAL,
        )
        wildcard_colors = sampler._wildcard_manager.get_all_values(command.wildcard)
        gen = sampler.generator_from_command(command)

        for color in wildcard_colors:
            assert next(gen) == color

    def test_random_sampling_method(self, sampler: RandomSampler):
        command = WildcardCommand("colors*", sampling_method=SamplingMethod.RANDOM)

        sampler._random = mock.Mock()
        gen = sampler.generator_from_command(command)
        random_choices = [
            LiteralCommand("red"),
            LiteralCommand("red"),
            LiteralCommand("yellow"),
            LiteralCommand("green"),
        ]

        sampler._random.choice.side_effect = random_choices
        prompts = [next(gen) for _ in range(4)]
        for c, prompt in zip(random_choices, prompts):
            assert c.literal == prompt

    def test_combinatorial_sampling_method_with_sequence(
        self,
        sampler_manager: ConcreteSamplerManager,
    ):
        command = SequenceCommand(
            [
                LiteralCommand("XXX"),
                WildcardCommand(
                    "colors*",
                    sampling_method=SamplingMethod.CYCLICAL,
                ),
            ],
        )

        prompts = list(sampler_manager.sample_prompts(command, 5))
        assert prompts == ["XXXblue", "XXXgreen", "XXXred", "XXXyellow", "XXXblue"]


class TestRandomGenerator:
    def test_variants_with_larger_bounds_than_choices(
        self,
        sampler: RandomSampler,
        sampler_manager: ConcreteSamplerManager,
    ):

        with mock.patch.object(sampler, "_get_choices") as mock_choices:
            sampler._random = mock.Mock()
            shapes = [LiteralCommand("square"), LiteralCommand("circle")]
            sampler._random.randint.return_value = 3
            mock_choices.side_effect = [shapes]
            prompts = list(
                sampler_manager.sample_prompts("A red {3$$square|circle}", 1),
            )

            assert len(prompts) == 1
            assert prompts[0] == "A red square,circle"

    def test_variants_with_pipe_separator(
        self,
        sampler: RandomSampler,
        sampler_manager: ConcreteSamplerManager,
    ):
        sampler._random = mock.Mock()
        shapes = [LiteralCommand("square"), LiteralCommand("circle")]
        with mock.patch.object(sampler, "_get_choices") as mock_choices:
            sampler._random.randint.return_value = 3
            mock_choices.side_effect = [shapes]
            assert list(
                sampler_manager.sample_prompts("A red {3$$|$$square|circle}", 1),
            ) == [
                "A red square|circle",
            ]

    def test_weighted_variant(
        self,
        sampler: RandomSampler,
        sampler_manager: ConcreteSamplerManager,
    ):
        sampler._random = mock.Mock()

        with mock.patch.object(sampler, "_get_choices") as mock_choices:
            mock_choices.return_value = [LiteralCommand("green")]
            sampler._random.randint.return_value = 1
            prompts = list(
                sampler_manager.sample_prompts("A {1::red|2::green|3::blue}", 1),
            )

            assert len(prompts) == 1
            assert prompts[0] == "A green"

    def test_wildcards(
        self,
        sampler: RandomSampler,
        sampler_manager: ConcreteSamplerManager,
    ):
        sampler._random = mock.Mock()
        with mock.patch.object(
            sampler._wildcard_manager,
            "get_all_values",
            return_value=SequenceCommand.from_literals(RED_GREEN_BLUE),
        ):
            with mock.patch.object(sampler, "_get_choices") as mock_choices:
                sampler._random.choice.side_effect = RED_AND_GREEN
                mock_choices.side_effect = [
                    [LiteralCommand("square")],
                    [LiteralCommand("circle")],
                ]
                assert list(
                    sampler_manager.sample_prompts("A __colours__ {square|circle}", 2),
                ) == [
                    "A red square",
                    "A green circle",
                ]

    def test_missing_wildcard(
        self,
        sampler: RandomSampler,
        sampler_manager: ConcreteSamplerManager,
    ):
        with mock.patch.object(
            sampler._wildcard_manager,
            "get_all_values",
            return_value=[],
        ):
            assert list(
                sampler_manager.sample_prompts("A __missing__ wildcard", 1),
            ) == [
                "A __missing__ wildcard",
            ]

    def test_nospace_before_or_after_wildcard(
        self,
        sampler: RandomSampler,
        sampler_manager: ConcreteSamplerManager,
    ):
        sampler._random = mock.Mock()
        with mock.patch.object(
            sampler._wildcard_manager,
            "get_all_values",
            return_value=SequenceCommand.from_literals(RED_GREEN_BLUE),
        ):
            sampler._random.choice.side_effect = RED_AND_GREEN
            assert list(sampler_manager.sample_prompts("(__colours__:2.3) ", 1)) == [
                "(red:2.3) ",
            ]
