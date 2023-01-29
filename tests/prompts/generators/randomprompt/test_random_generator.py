from unittest import mock

import pytest
from dynamicprompts.commands import (
    LiteralCommand,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.parser.random_generator import RandomGenerator

from tests.prompts.consts import ONE_TWO_THREE, RED_AND_GREEN, RED_GREEN_BLUE, SHAPES


@pytest.fixture
def generator(wildcard_manager) -> RandomGenerator:
    return RandomGenerator(wildcard_manager=wildcard_manager)


class TestRandomSequenceCommand:
    def test_prompts(self, generator: RandomGenerator):
        sequence = SequenceCommand.from_literals(["one", " ", "two", " ", "three"])
        prompt = next(generator.generator_from_command(sequence))
        assert prompt == "one two three"


class TestVariantCommand:
    def test_empty_variant(self, generator: RandomGenerator):
        command = VariantCommand([])
        prompts = list(generator.generator_from_command(command))
        assert len(prompts) == 0

    def test_single_variant(self, generator: RandomGenerator):
        command = VariantCommand.from_literals_and_weights(["one"])
        prompt = next(generator.generator_from_command(command))
        assert prompt == "one"

    def test_multiple_variant(self, generator: RandomGenerator):
        command = VariantCommand.from_literals_and_weights(ONE_TWO_THREE)
        generator._random = mock.Mock()
        random_choices = [
            [LiteralCommand("one")],
            [LiteralCommand("three")],
            [LiteralCommand("two")],
            [LiteralCommand("one")],
        ]
        generator._random.choices.side_effect = random_choices

        for c in random_choices:
            prompt = next(generator.generator_from_command(command))
            assert prompt == c[0].literal

    def test_variant_with_literal(self, generator: RandomGenerator):
        command1 = VariantCommand.from_literals_and_weights(ONE_TWO_THREE)
        command2 = LiteralCommand(" ")
        command3 = LiteralCommand("circles")
        sequence = SequenceCommand([command1, command2, command3])
        generator._random = mock.Mock()

        random_choices = [
            [LiteralCommand("one")],
            [LiteralCommand("three")],
            [LiteralCommand("two")],
            [LiteralCommand("one")],
        ]
        generator._random.choices.side_effect = random_choices
        for c in random_choices:
            prompt = next(generator.generator_from_command(sequence))
            assert prompt == f"{c[0].literal} circles"

    def test_variant_with_bound(self, generator: RandomGenerator):
        variant_values = ONE_TWO_THREE
        command1 = VariantCommand.from_literals_and_weights(
            variant_values,
            min_bound=1,
            max_bound=2,
        )
        generator._random = mock.Mock()

        random_choices = [
            [LiteralCommand("one")],
            [LiteralCommand("two"), LiteralCommand("one")],
            [LiteralCommand("three")],
            [LiteralCommand("three"), LiteralCommand("one")],
        ]
        generator._random.choices.side_effect = random_choices
        generator._random.randint.side_effect = [1, 2, 1, 2]

        gen = generator.generator_from_command(command1)
        for c in random_choices:
            assert next(gen) == ",".join([v.literal for v in c])

    def test_variant_with_bound_and_sep(self, generator: RandomGenerator):
        command1 = VariantCommand.from_literals_and_weights(
            ONE_TWO_THREE,
            min_bound=1,
            max_bound=2,
            separator=" and ",
        )
        generator._random = mock.Mock()

        random_choices = [LiteralCommand("two"), LiteralCommand("one")]
        generator._random.choices.return_value = random_choices
        generator._random.randint.side_effect = [2]

        prompt = next(generator.generator_from_command(command1))
        assert prompt == "two and one"

    def test_two_variants(self, generator: RandomGenerator):
        command1 = VariantCommand.from_literals_and_weights(RED_AND_GREEN)
        command2 = LiteralCommand(" ")
        command3 = VariantCommand.from_literals_and_weights(SHAPES)
        sequence = SequenceCommand([command1, command2, command3])
        expected_combos = {
            f"{color} {shape}" for color in RED_AND_GREEN for shape in SHAPES
        }
        generated_combos = set()
        gen = generator.generator_from_command(sequence)
        # This could technically loop forever if the underlying RNG is broken,
        # but we'll take our chances.
        while generated_combos != expected_combos:
            generated_combos.add(next(gen))

    def test_varied_prompt(self, generator: RandomGenerator):
        command1 = VariantCommand.from_literals_and_weights(RED_AND_GREEN)
        command3 = VariantCommand.from_literals_and_weights(SHAPES)
        sequence = SequenceCommand.from_literals(
            [command1, " ", command3, " ", "are", " ", "cool"],
        )

        generator._random = mock.Mock()
        generator._random.choices.side_effect = [
            [LiteralCommand("red")],
            [LiteralCommand("squares")],
            [LiteralCommand("green")],
            [LiteralCommand("triangles")],
        ]
        gen = generator.generator_from_command(sequence)

        assert next(gen) == "red squares are cool"
        assert next(gen) == "green triangles are cool"


class TestWildcardsCommand:
    def test_basic_wildcard(self, generator: RandomGenerator):
        command = WildcardCommand("colors*")
        wildcard_colors = set(
            generator._wildcard_manager.get_all_values(command.wildcard),
        )
        generated_values = set()
        gen = generator.generator_from_command(command)
        # This could technically loop forever if the underlying RNG is broken,
        # but we'll take our chances.
        while generated_values != wildcard_colors:
            generated_values.add(next(gen))

    def test_wildcard_with_literal(self, generator: RandomGenerator):
        command = WildcardCommand("colors*")
        sequence = SequenceCommand.from_literals(
            [command, " ", "are", " ", LiteralCommand("cool")],
        )
        wildcard_colors = set(
            generator._wildcard_manager.get_all_values(command.wildcard),
        )
        generated_values = set()
        gen = generator.generator_from_command(sequence)
        # This could technically loop forever if the underlying RNG is broken,
        # but we'll take our chances.
        while len(generated_values) < len(wildcard_colors):
            prompt = next(gen)
            color, _, rest = prompt.partition(" ")
            assert color in wildcard_colors
            assert rest == "are cool"
            generated_values.add(prompt)

    def test_wildcard_with_variant(self, generator: RandomGenerator):
        command1 = WildcardCommand("colors*")
        wildcard_colors = set(
            generator._wildcard_manager.get_all_values(command1.wildcard),
        )
        total_count = len(wildcard_colors) * len(SHAPES)
        command3 = VariantCommand.from_literals_and_weights(SHAPES)
        command3._random = mock.Mock()
        sequence = SequenceCommand.from_literals([command1, " ", command3])
        generated_values = set()
        gen = generator.generator_from_command(sequence)
        # This could technically loop forever if the underlying RNG is broken,
        # but we'll take our chances.
        while len(generated_values) < total_count:
            prompt = next(gen)
            color, _, shape = prompt.partition(" ")
            assert color in wildcard_colors
            assert shape in SHAPES
            generated_values.add(prompt)


class TestRandomGenerator:
    def test_empty(self, generator: RandomGenerator):
        prompts = list(generator.generate_prompts("", 5))
        assert len(prompts) == 0

    def test_literals(self, generator: RandomGenerator):
        sentence = "A literal sentence"
        assert list(generator.generate_prompts(sentence, 5)) == [sentence] * 5

    def test_literal_with_square_brackets(self, generator: RandomGenerator):
        prompts = list(generator.generate_prompts("Test [low emphasis]", 1))
        assert len(prompts) == 1
        assert prompts[0] == "Test [low emphasis]"

    def test_variants(self, generator: RandomGenerator):
        expected_prompts = {"A red square", "A red circle"}
        generated_prompts = set()
        while generated_prompts != expected_prompts:
            prompts = list(generator.generate_prompts("A red {square|circle}", 5))
            assert len(prompts) == 5  # should generate 5 prompts when asked to
            assert all(p in expected_prompts for p in prompts)
            generated_prompts.update(prompts)

    def test_variant_with_blank(self, generator: RandomGenerator):
        expected_prompts = {"A  rose", "A red rose", "A blue rose"}
        generated_prompts = set()
        while generated_prompts != expected_prompts:
            prompts = list(generator.generate_prompts("A {red|blue|} rose", 5))
            assert len(prompts) == 5
            assert all(p in expected_prompts for p in prompts)
            generated_prompts.update(prompts)

    def test_variants_with_bounds(self, generator: RandomGenerator):
        generator._random = mock.Mock()
        shapes = [LiteralCommand("square"), LiteralCommand("circle")]

        generator._random.randint.return_value = 2
        generator._random.choices.side_effect = [shapes]
        assert list(generator.generate_prompts("A red {2$$square|circle}", 1)) == [
            "A red square,circle",
        ]

    def test_variants_with_larger_bounds_than_choices(self, generator: RandomGenerator):
        generator._random = mock.Mock()
        shapes = [LiteralCommand("square"), LiteralCommand("circle")]
        generator._random.randint.return_value = 3
        generator._random.choices.side_effect = [shapes]
        prompts = list(generator.generate_prompts("A red {3$$square|circle}", 1))

        assert len(prompts) == 1
        assert prompts[0] == "A red square,circle"

    def test_variants_with_pipe_separator(self, generator: RandomGenerator):
        generator._random = mock.Mock()
        shapes = [LiteralCommand("square"), LiteralCommand("circle")]
        generator._random.randint.return_value = 3
        generator._random.choices.side_effect = [shapes]
        assert list(generator.generate_prompts("A red {3$$|$$square|circle}", 1)) == [
            "A red square|circle",
        ]

    def test_two_variants(self, generator: RandomGenerator):
        with mock.patch(
            "dynamicprompts.parser.random_generator.DEFAULT_RANDOM.choices",
        ) as mock_random:
            mock_random.side_effect = [
                [LiteralCommand("green")],
                [LiteralCommand("square")],
                [LiteralCommand("green")],
                [LiteralCommand("circle")],
            ]
            assert list(
                generator.generate_prompts("A {red|green} {square|circle}", 2),
            ) == [
                "A green square",
                "A green circle",
            ]

    def test_weighted_variant(self, generator: RandomGenerator):
        generator._random = mock.Mock()

        generator._random.choices.return_value = [LiteralCommand("green")]
        generator._random.randint.return_value = 1
        prompts = list(generator.generate_prompts("A {1::red|2::green|3::blue}", 1))

        assert len(prompts) == 1
        assert prompts[0] == "A green"

    def test_wildcards(self, generator: RandomGenerator):
        generator._random = mock.Mock()
        with mock.patch.object(
            generator._wildcard_manager,
            "get_all_values",
            return_value=SequenceCommand.from_literals(RED_GREEN_BLUE),
        ):
            generator._random.choice.side_effect = RED_AND_GREEN
            generator._random.choices.side_effect = [
                [LiteralCommand("square")],
                [LiteralCommand("circle")],
            ]
            assert list(
                generator.generate_prompts("A __colours__ {square|circle}", 2),
            ) == [
                "A red square",
                "A green circle",
            ]

    def test_missing_wildcard(self, generator: RandomGenerator):
        with mock.patch.object(
            generator._wildcard_manager,
            "get_all_values",
            return_value=[],
        ):
            assert list(generator.generate_prompts("A __missing__ wildcard", 1)) == [
                "A __missing__ wildcard",
            ]

    def test_nospace_before_or_after_wildcard(self, generator: RandomGenerator):
        generator._random = mock.Mock()
        with mock.patch.object(
            generator._wildcard_manager,
            "get_all_values",
            return_value=SequenceCommand.from_literals(RED_GREEN_BLUE),
        ):
            generator._random.choice.side_effect = RED_AND_GREEN
            assert list(generator.generate_prompts("(__colours__:2.3) ", 1)) == [
                "(red:2.3) ",
            ]
