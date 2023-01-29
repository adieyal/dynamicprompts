from __future__ import annotations

from unittest import mock

import pytest
from dynamicprompts.commands import (
    LiteralCommand,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.parser.combinatorial_generator import CombinatorialGenerator
from dynamicprompts.wildcardmanager import WildcardManager

from tests.prompts.consts import ONE_TWO_THREE, RED_AND_GREEN, RED_GREEN_BLUE, SHAPES


@pytest.fixture
def generator(wildcard_manager: WildcardManager) -> CombinatorialGenerator:
    return CombinatorialGenerator(wildcard_manager=wildcard_manager)


class TestLiteralCommand:
    def test_iter_with_no_next(self, generator: CombinatorialGenerator):
        command = LiteralCommand("test")
        prompts = list(generator.generate_prompts(command))
        assert len(prompts) == 1
        assert prompts[0] == "test"

    def test_iter_with_next(self, generator: CombinatorialGenerator):
        sequence = SequenceCommand.from_literals(["one", " ", "two", " ", "three"])
        prompts = list(generator.generate_prompts(sequence))
        assert len(prompts) == 1
        assert prompts[0] == "one two three"

    def test_prompts(self, generator: CombinatorialGenerator):
        command = LiteralCommand("test")
        assert list(generator.generate_prompts(command)) == ["test"]


class TestVariantCommand:
    def test_empty_variant(self, generator: CombinatorialGenerator):
        command = VariantCommand([])
        prompts = list(generator.generate_prompts(command))
        assert len(prompts) == 0

    def test_single_variant(self, generator: CombinatorialGenerator):
        command = VariantCommand.from_literals_and_weights(["one"])
        prompts = list(generator.generate_prompts(command))

        assert len(prompts) == 1
        assert prompts[0] == "one"

    def test_multiple_variant(self, generator: CombinatorialGenerator):
        command = VariantCommand.from_literals_and_weights(ONE_TWO_THREE)
        prompts = list(generator.generate_prompts(command))
        assert len(prompts) == 3
        assert prompts[0] == "one"
        assert prompts[1] == "two"
        assert prompts[2] == "three"

    def test_variant_with_literal(self, generator: CombinatorialGenerator):
        command1 = VariantCommand.from_literals_and_weights(ONE_TWO_THREE)
        command2 = LiteralCommand(" circles and squares")
        sequence = SequenceCommand([command1, command2])

        prompts = list(generator.generate_prompts(sequence))
        assert len(prompts) == 3
        assert prompts[0] == "one circles and squares"
        assert prompts[1] == "two circles and squares"
        assert prompts[2] == "three circles and squares"

    def test_two_variants(self, generator: CombinatorialGenerator):
        command1 = VariantCommand.from_literals_and_weights(RED_AND_GREEN)
        command2 = VariantCommand.from_literals_and_weights(SHAPES)
        space = LiteralCommand(" ")
        sequence = SequenceCommand([command1, space, command2])

        prompts = list(generator.generate_prompts(sequence))
        assert len(prompts) == 6
        assert prompts[0] == "red circles"
        assert prompts[1] == "red squares"
        assert prompts[2] == "red triangles"
        assert prompts[3] == "green circles"
        assert prompts[4] == "green squares"
        assert prompts[5] == "green triangles"

    def test_varied_prompt(self, generator: CombinatorialGenerator):
        command1 = VariantCommand.from_literals_and_weights(RED_AND_GREEN)
        command2 = VariantCommand.from_literals_and_weights(SHAPES)
        space = LiteralCommand(" ")
        command3 = LiteralCommand(" are cool")
        sequence = SequenceCommand([command1, space, command2, command3])

        prompts = list(generator.generate_prompts(sequence))

        assert len(prompts) == 6
        assert prompts[0] == "red circles are cool"
        assert prompts[1] == "red squares are cool"
        assert prompts[2] == "red triangles are cool"
        assert prompts[3] == "green circles are cool"
        assert prompts[4] == "green squares are cool"
        assert prompts[5] == "green triangles are cool"

    def test_combo(self, generator: CombinatorialGenerator):
        command = VariantCommand.from_literals_and_weights(
            RED_GREEN_BLUE,
            min_bound=2,
            max_bound=2,
        )
        prompts = list(generator.generate_prompts(command))
        assert len(prompts) == 6
        assert prompts[0] == "red,green"
        assert prompts[1] == "red,blue"
        assert prompts[2] == "green,red"
        assert prompts[3] == "green,blue"
        assert prompts[4] == "blue,red"
        assert prompts[5] == "blue,green"

    def test_combo_different_bounds(self, generator: CombinatorialGenerator):
        command = VariantCommand.from_literals_and_weights(
            RED_GREEN_BLUE,
            min_bound=1,
            max_bound=2,
        )
        prompts = list(generator.generate_prompts(command))
        assert len(prompts) == 9
        assert prompts[0] == "red"
        assert prompts[1] == "green"
        assert prompts[2] == "blue"
        assert prompts[3] == "red,green"
        assert prompts[4] == "red,blue"
        assert prompts[5] == "green,red"
        assert prompts[6] == "green,blue"
        assert prompts[7] == "blue,red"
        assert prompts[8] == "blue,green"

    def test_custom_sep(self, generator: CombinatorialGenerator):
        command = VariantCommand.from_literals_and_weights(
            RED_GREEN_BLUE,
            min_bound=2,
            max_bound=2,
            separator=" and ",
        )
        prompts = list(generator.generate_prompts(command))
        assert len(prompts) == 6
        assert prompts[0] == "red and green"
        assert prompts[1] == "red and blue"
        assert prompts[2] == "green and red"
        assert prompts[3] == "green and blue"
        assert prompts[4] == "blue and red"
        assert prompts[5] == "blue and green"


class TestWildcardsCommand:
    def test_basic_wildcard(self, generator: CombinatorialGenerator):
        with mock.patch.object(
            generator._wildcard_manager,
            "get_all_values",
            return_value=RED_GREEN_BLUE,
        ):
            command = WildcardCommand("colours")
            prompts = list(generator.generate_prompts(command))
            assert len(prompts) == 3
            assert prompts[0] == "red"
            assert prompts[1] == "green"
            assert prompts[2] == "blue"

            generator._wildcard_manager.get_all_values.assert_called_once_with(
                "colours",
            )

    def test_wildcard_with_literal(self, generator: CombinatorialGenerator):
        with mock.patch.object(
            generator._wildcard_manager,
            "get_all_values",
            return_value=RED_GREEN_BLUE,
        ):
            command1 = WildcardCommand("colours")
            command2 = LiteralCommand(" are cool")
            sequence = SequenceCommand([command1, command2])

            prompts = list(generator.generate_prompts(sequence))
            assert len(prompts) == 3
            assert prompts[0] == "red are cool"
            assert prompts[1] == "green are cool"
            assert prompts[2] == "blue are cool"
            generator._wildcard_manager.get_all_values.assert_called_once_with(
                "colours",
            )

    def test_wildcard_with_variant(self, generator: CombinatorialGenerator):
        with mock.patch.object(
            generator._wildcard_manager,
            "get_all_values",
            return_value=RED_GREEN_BLUE,
        ):
            command1 = WildcardCommand("colours")
            space = LiteralCommand(" ")
            command2 = VariantCommand.from_literals_and_weights(["circles", "squares"])
            sequence = SequenceCommand([command1, space, command2])

            prompts = list(generator.generate_prompts(sequence))

            assert len(prompts) == 6
            assert prompts[0] == "red circles"
            assert prompts[1] == "red squares"
            assert prompts[2] == "green circles"
            assert prompts[3] == "green squares"
            assert prompts[4] == "blue circles"
            assert prompts[5] == "blue squares"

    def test_variant_nested_in_wildcard(self, generator: CombinatorialGenerator):
        with mock.patch.object(
            generator._wildcard_manager,
            "get_all_values",
            return_value=["{red|pink}", "green", "blue"],
        ):
            wildcard_command = WildcardCommand("colours")
            sequence = SequenceCommand([wildcard_command])

            prompts = list(generator.generate_prompts(sequence))

            assert len(prompts) == 4
            assert prompts[0] == "red"
            assert prompts[1] == "pink"
            assert prompts[2] == "green"
            assert prompts[3] == "blue"

    def test_wildcard_nested_in_wildcard(self, generator: CombinatorialGenerator):
        with mock.patch.object(
            generator._wildcard_manager,
            "get_all_values",
            side_effect=[
                ["__other_colours__", "green", "blue"],
                ["red", "pink", "yellow"],
            ],
        ):
            wildcard_command = WildcardCommand("colours")
            sequence = SequenceCommand([wildcard_command])

            prompts = list(generator.generate_prompts(sequence))

            assert len(prompts) == 5
            assert prompts[0] == "red"
            assert prompts[1] == "pink"
            assert prompts[2] == "yellow"
            assert prompts[3] == "green"
            assert prompts[4] == "blue"


class TestSequenceCommand:
    def test_prompts(self, generator: CombinatorialGenerator):
        command1 = LiteralCommand("A")
        command2 = LiteralCommand("sentence")
        space = LiteralCommand(" ")
        sequence = SequenceCommand([command1, space, command2])

        prompts = list(generator.generate_prompts(sequence))
        assert len(prompts) == 1
        assert prompts[0] == "A sentence"

    def test_custom_separator(self, generator: CombinatorialGenerator):
        command1 = LiteralCommand("A")
        command2 = LiteralCommand("sentence")
        sequence = SequenceCommand([command1, command2], separator="")

        prompts = list(generator.generate_prompts(sequence))
        assert len(prompts) == 1
        assert prompts[0] == "Asentence"


class TestGenerator:
    def test_empty(self, generator: CombinatorialGenerator):
        prompts = generator.generate_prompts("", 5)
        assert len(prompts) == 0

    def test_literals(self, generator: CombinatorialGenerator):
        prompts = list(generator.generate_prompts("A literal sentence", 5))
        assert len(prompts) == 1

    def test_literal_with_square_brackets(self, generator: CombinatorialGenerator):
        prompts = list(generator.generate_prompts("Test [low emphasis]", 1))
        assert len(prompts) == 1
        assert prompts[0] == "Test [low emphasis]"

    def test_variants(self, generator: CombinatorialGenerator):
        prompts = list(generator.generate_prompts("A red {square|circle}", 5))
        assert len(prompts) == 2
        assert prompts[0] == "A red square"
        assert prompts[1] == "A red circle"

    def test_variant_with_blank(self, generator: CombinatorialGenerator):
        prompts = list(generator.generate_prompts("A {|red|blue} rose", 3))
        assert len(prompts) == 3
        assert prompts[0] == "A  rose"
        assert prompts[1] == "A red rose"
        assert prompts[2] == "A blue rose"

    def test_two_variants(self, generator: CombinatorialGenerator):
        prompts = list(generator.generate_prompts("A {red|green} {square|circle}", 5))
        assert len(prompts) == 4
        assert prompts[0] == "A red square"
        assert prompts[1] == "A red circle"
        assert prompts[2] == "A green square"
        assert prompts[3] == "A green circle"

        prompts = list(generator.generate_prompts("A {red|green} {square|circle}", 2))
        assert len(prompts) == 2
        assert prompts[0] == "A red square"
        assert prompts[1] == "A red circle"

    def test_combination_variants(self, generator: CombinatorialGenerator):
        prompts = list(generator.generate_prompts("A {2$$red|green|blue} square", 10))
        assert len(prompts) == 6
        assert prompts[0] == "A red,green square"
        assert prompts[1] == "A red,blue square"
        assert prompts[2] == "A green,red square"
        assert prompts[3] == "A green,blue square"
        assert prompts[4] == "A blue,red square"
        assert prompts[5] == "A blue,green square"

    def test_combination_variants_range(self, generator: CombinatorialGenerator):
        prompts = list(generator.generate_prompts("A {1-2$$red|green|blue} square", 10))
        assert len(prompts) == 9
        assert prompts[0] == "A red square"
        assert prompts[1] == "A green square"
        assert prompts[2] == "A blue square"
        assert prompts[3] == "A red,green square"
        assert prompts[4] == "A red,blue square"
        assert prompts[5] == "A green,red square"
        assert prompts[6] == "A green,blue square"
        assert prompts[7] == "A blue,red square"
        assert prompts[8] == "A blue,green square"

    def test_combination_variants_with_separator(
        self,
        generator: CombinatorialGenerator,
    ):
        prompts = list(
            generator.generate_prompts("A {2$$ and $$red|green|blue} square", 10),
        )
        assert len(prompts) == 6
        assert prompts[0] == "A red and green square"
        assert prompts[1] == "A red and blue square"
        assert prompts[2] == "A green and red square"
        assert prompts[3] == "A green and blue square"
        assert prompts[4] == "A blue and red square"
        assert prompts[5] == "A blue and green square"

    def test_variants_with_larger_range_than_choices(
        self,
        generator: CombinatorialGenerator,
    ):
        shapes = ["square", "circle"]
        with mock.patch(
            "dynamicprompts.parser.random_generator.DEFAULT_RANDOM",
        ) as mock_random:
            mock_random.randint.return_value = 3
            mock_random.choices.side_effect = [shapes]
            prompts = list(generator.generate_prompts("A red {3$$square|circle}", 1))

            assert len(prompts) == 0

    def test_wildcards(self, generator: CombinatorialGenerator):
        with mock.patch.object(
            generator._wildcard_manager,
            "get_all_values",
            return_value=RED_GREEN_BLUE,
        ):
            prompts = list(
                generator.generate_prompts("A __colours__ {square|circle}", 6),
            )
            assert len(prompts) == 6
            assert prompts[0] == "A red square"
            assert prompts[1] == "A red circle"
            assert prompts[2] == "A green square"
            assert prompts[3] == "A green circle"
            assert prompts[4] == "A blue square"
            assert prompts[5] == "A blue circle"
            generator._wildcard_manager.get_all_values.assert_called_once_with(
                "colours",
            )

    def test_nested_wildcard(self, generator: CombinatorialGenerator):
        with mock.patch.object(
            generator._wildcard_manager,
            "get_all_values",
            return_value=RED_GREEN_BLUE,
        ):
            prompts = list(generator.generate_prompts("{__colours__}", 6))
            assert len(prompts) == 3

    def test_nested_wildcard_with_range(self, generator: CombinatorialGenerator):
        with mock.patch.object(
            generator._wildcard_manager,
            "get_all_values",
            return_value=RED_GREEN_BLUE,
        ):
            prompts = list(generator.generate_prompts("{2$$__colours__}", 6))
            assert len(prompts) == 6
            assert prompts[0] == "red,green"
            assert prompts[1] == "red,blue"
            assert prompts[2] == "green,red"
            assert prompts[3] == "green,blue"
            assert prompts[4] == "blue,red"
            assert prompts[5] == "blue,green"

    def test_nested_wildcard_with_range_and_literal(
        self,
        generator: CombinatorialGenerator,
    ):
        with mock.patch.object(
            generator._wildcard_manager,
            "get_all_values",
            return_value=RED_GREEN_BLUE,
        ):
            prompts = list(generator.generate_prompts("{2$$__colours__|black}", 20))
            assert len(prompts) == 12
            assert prompts[0] == "red,green"
            assert prompts[1] == "red,blue"
            assert prompts[2] == "green,red"
            assert prompts[3] == "green,blue"
            assert prompts[4] == "blue,red"
            assert prompts[5] == "blue,green"
            assert prompts[6] == "red,black"
            assert prompts[7] == "green,black"
            assert prompts[8] == "blue,black"
            assert prompts[9] == "black,red"
            assert prompts[10] == "black,green"
            assert prompts[11] == "black,blue"
