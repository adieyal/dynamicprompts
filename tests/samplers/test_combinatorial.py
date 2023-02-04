from __future__ import annotations

from unittest import mock

import pytest
from dynamicprompts.commands import (
    LiteralCommand,
    SamplingMethod,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.samplers.combinatorial import CombinatorialSampler
from dynamicprompts.samplers.sampler_manager import ConcreteSamplerManager
from dynamicprompts.wildcardmanager import WildcardManager

from tests.consts import ONE_TWO_THREE, RED_AND_GREEN, RED_GREEN_BLUE, SHAPES


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


class TestLiteralCommand:
    def test_single_literal(self, sampler_manager: ConcreteSamplerManager):
        command = LiteralCommand("test")
        prompts = list(sampler_manager.generator_from_command(command))

        assert prompts == ["test"]

    def test_multiple_literals(self, sampler_manager: ConcreteSamplerManager):
        sequence = SequenceCommand.from_literals(["one", " ", "two", " ", "three"])
        prompts = list(sampler_manager.generator_from_command(sequence))
        assert prompts == ["one two three"]


class TestVariantCommand:
    def test_empty_variant(self, sampler_manager: ConcreteSamplerManager):
        command = VariantCommand([])
        prompts = list(sampler_manager.generator_from_command(command))
        assert len(prompts) == 0

    def test_single_variant(self, sampler_manager: ConcreteSamplerManager):
        command = VariantCommand.from_literals_and_weights(["one"])
        prompts = list(sampler_manager.generator_from_command(command))

        assert prompts == ["one"]

    def test_multiple_variant(self, sampler_manager: ConcreteSamplerManager):
        command = VariantCommand.from_literals_and_weights(ONE_TWO_THREE)
        prompts = list(sampler_manager.generator_from_command(command))

        assert prompts == ["one", "two", "three"]

    #     def test_sampling_method(self, sampler_manager: ConcreteSamplerManager):
    #         command = VariantCommand.from_literals_and_weights(
    #             ONE_TWO_THREE,
    #             sampling_method=SamplingMethod.COMBINATORIAL,
    #         )
    #         prompts = list(sampler_manager.generator_from_command())
    #         assert prompts == ONE_TWO_THREE

    #         command = VariantCommand.from_literals_and_weights(
    #             ONE_TWO_THREE,
    #             sampling_method=SamplingMethod.RANDOM,
    #         )
    #         mock_rand = mock.Mock()
    #         defaults = {"ignore_whitespace": False, "rand": mock_rand}
    #         with mock.patch.object(
    #             RandomSampler.__init__,
    #             "__kwdefaults__",
    #             defaults,
    #         ):
    #             random_choices = [
    #                 [LiteralCommand("one")],
    #                 [LiteralCommand("three")],
    #                 [LiteralCommand("two")],
    #                 [LiteralCommand("one")],
    #             ]
    #             mock_rand.choices.side_effect = random_choices
    #             prompts = sampler_manager.generator_from_command()

    #             for c in random_choices:
    #                 prompt = next(sampler.generator_from_command(command))
    #                 assert prompt == c[0].literal

    def test_variant_with_literal(self, sampler_manager: ConcreteSamplerManager):
        command1 = VariantCommand.from_literals_and_weights(ONE_TWO_THREE)
        command2 = LiteralCommand(" circles and squares")
        sequence = SequenceCommand([command1, command2])

        prompts = list(sampler_manager.generator_from_command(sequence))
        assert prompts == [
            "one circles and squares",
            "two circles and squares",
            "three circles and squares",
        ]

    def test_two_variants(self, sampler_manager: ConcreteSamplerManager):
        command1 = VariantCommand.from_literals_and_weights(RED_AND_GREEN)
        command2 = VariantCommand.from_literals_and_weights(SHAPES)
        space = LiteralCommand(" ")
        sequence = SequenceCommand([command1, space, command2])

        prompts = list(sampler_manager.generator_from_command(sequence))
        assert prompts == [
            "red circles",
            "red squares",
            "red triangles",
            "green circles",
            "green squares",
            "green triangles",
        ]

    def test_varied_prompt(self, sampler_manager: ConcreteSamplerManager):
        command1 = VariantCommand.from_literals_and_weights(RED_AND_GREEN)
        command2 = VariantCommand.from_literals_and_weights(SHAPES)
        space = LiteralCommand(" ")
        command3 = LiteralCommand(" are cool")
        sequence = SequenceCommand([command1, space, command2, command3])

        prompts = list(sampler_manager.generator_from_command(sequence))
        assert prompts == [
            "red circles are cool",
            "red squares are cool",
            "red triangles are cool",
            "green circles are cool",
            "green squares are cool",
            "green triangles are cool",
        ]

    def test_combo(self, sampler_manager: ConcreteSamplerManager):
        command = VariantCommand.from_literals_and_weights(
            RED_GREEN_BLUE,
            min_bound=2,
            max_bound=2,
        )
        prompts = list(sampler_manager.generator_from_command(command))
        assert prompts == [
            "red,green",
            "red,blue",
            "green,red",
            "green,blue",
            "blue,red",
            "blue,green",
        ]

    def test_combo_different_bounds(self, sampler_manager: ConcreteSamplerManager):
        command = VariantCommand.from_literals_and_weights(
            RED_GREEN_BLUE,
            min_bound=1,
            max_bound=2,
        )
        prompts = list(sampler_manager.generator_from_command(command))

        assert prompts == [
            "red",
            "green",
            "blue",
            "red,green",
            "red,blue",
            "green,red",
            "green,blue",
            "blue,red",
            "blue,green",
        ]

    def test_custom_sep(self, sampler_manager: ConcreteSamplerManager):
        command = VariantCommand.from_literals_and_weights(
            RED_GREEN_BLUE,
            min_bound=2,
            max_bound=2,
            separator=" and ",
        )
        prompts = list(sampler_manager.generator_from_command(command))
        assert prompts == [
            "red and green",
            "red and blue",
            "green and red",
            "green and blue",
            "blue and red",
            "blue and green",
        ]


class TestWildcardsCommand:
    def test_basic_wildcard(self, sampler_manager: ConcreteSamplerManager):

        command = WildcardCommand("colours")
        prompts = list(sampler_manager.generator_from_command(command))
        assert prompts == RED_GREEN_BLUE

        sampler_manager._wildcard_manager.get_all_values.assert_called_once_with(
            "colours",
        )

    #     def test_sampling_method(self, sampler_manager: ConcreteSamplerManager):
    #         with mock.patch.object(
    #             sampler_manager._wildcard_manager,
    #             "get_all_values",
    #             return_value=RED_GREEN_BLUE,
    #         ):
    #             command = WildcardCommand(
    #                 "colours",
    #                 sampling_method=SamplingMethod.COMBINATORIAL,
    #             )
    #             prompts = list(sampler_manager.generator_from_command())

    #             assert prompts == RED_GREEN_BLUE

    #             command = WildcardCommand("colours", sampling_method=SamplingMethod.RANDOM)
    #             mock_rand = mock.Mock()
    #             defaults = {"ignore_whitespace": False, "rand": mock_rand}
    #             with mock.patch.object(
    #                 RandomSampler.__init__,
    #                 "__kwdefaults__",
    #                 defaults,
    #             ):
    #                 random_choices = [
    #                     LiteralCommand("red"),
    #                     LiteralCommand("red"),
    #                     LiteralCommand("green"),
    #                     LiteralCommand("blue"),
    #                 ]
    #                 mock_rand.choice.side_effect = random_choices
    #                 prompts = sampler_manager.generator_from_command()

    #                 for c in random_choices:
    #                     prompt = next(sampler.generator_from_command(command))
    #                     assert prompt == c.literal

    def test_wildcard_with_literal(self, sampler_manager: ConcreteSamplerManager):
        command1 = WildcardCommand("colours")
        command2 = LiteralCommand(" are cool")
        sequence = SequenceCommand([command1, command2])

        prompts = list(sampler_manager.generator_from_command(sequence))

        assert prompts == [
            "red are cool",
            "green are cool",
            "blue are cool",
        ]

        sampler_manager._wildcard_manager.get_all_values.assert_called_once_with(
            "colours",
        )

    def test_wildcard_with_variant(self, sampler_manager: ConcreteSamplerManager):

        command1 = WildcardCommand("colours")
        space = LiteralCommand(" ")
        command2 = VariantCommand.from_literals_and_weights(["circles", "squares"])
        sequence = SequenceCommand([command1, space, command2])

        prompts = list(sampler_manager.generator_from_command(sequence))
        assert prompts == [
            "red circles",
            "red squares",
            "green circles",
            "green squares",
            "blue circles",
            "blue squares",
        ]

    def test_variant_nested_in_wildcard(self, sampler_manager: ConcreteSamplerManager):
        with mock.patch.object(
            sampler_manager._wildcard_manager,
            "get_all_values",
            return_value=["{red|pink}", "green", "blue"],
        ):
            wildcard_command = WildcardCommand("colours")
            sequence = SequenceCommand([wildcard_command])

            prompts = list(sampler_manager.generator_from_command(sequence))
            assert prompts == ["red", "pink", "green", "blue"]

    def test_wildcard_nested_in_wildcard(self, sampler_manager: ConcreteSamplerManager):
        test_colours = [
            ["__other_colours__", "green", "blue"],
            ["red", "pink", "yellow"],
        ]

        with mock.patch.object(
            sampler_manager._wildcard_manager,
            "get_all_values",
            side_effect=test_colours,
        ):
            wildcard_command = WildcardCommand("colours")
            sequence = SequenceCommand([wildcard_command])

            prompts = list(sampler_manager.generator_from_command(sequence))
            assert prompts == ["red", "pink", "yellow", "green", "blue"]


class TestSequenceCommand:
    def test_prompts(self, sampler_manager: ConcreteSamplerManager):
        command1 = LiteralCommand("A")
        command2 = LiteralCommand("sentence")
        space = LiteralCommand(" ")
        sequence = SequenceCommand([command1, space, command2])

        prompts = list(sampler_manager.generator_from_command(sequence))
        assert prompts == ["A sentence"]

    def test_custom_separator(self, sampler_manager: ConcreteSamplerManager):
        command1 = LiteralCommand("A")
        command2 = LiteralCommand("sentence")
        sequence = SequenceCommand([command1, command2], separator="")

        prompts = list(sampler_manager.generator_from_command(sequence))
        assert prompts == ["Asentence"]


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
