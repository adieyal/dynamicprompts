from typing import cast
from unittest import mock

import pytest
from dynamicprompts.parser.commands import LiteralCommand
from dynamicprompts.parser.random_generator import (
    RandomActionBuilder,
    RandomGenerator,
    RandomSequenceCommand,
    RandomVariantCommand,
    RandomWildcardCommand,
)


def to_seqlit(*args):
    args = [LiteralCommand(a) for a in args]
    return RandomSequenceCommand(args)


@pytest.fixture
def wildcard_manager():
    return mock.Mock()


@pytest.fixture
def builder(wildcard_manager):
    return RandomActionBuilder(wildcard_manager)


@pytest.fixture
def generator(wildcard_manager):
    return RandomGenerator(wildcard_manager)


def gen_variant(vals, weights=None):
    vals = [to_seqlit(v) for v in vals]
    if weights is None:
        weights = [1] * len(vals)
    return [{"weight": [w], "val": v} for (w, v) in zip(weights, vals)]


class TestRandomSequenceCommand:
    def test_prompts(self):
        sequence = to_seqlit("one", " ", "two", " ", "three")
        prompts = list(sequence.prompts())

        assert len(prompts) == 1
        assert prompts[0] == "one two three"


class TestVariantCommand:
    def test_empty_variant(self):
        command = RandomVariantCommand([])
        prompts = list(command.prompts())
        assert len(prompts) == 0

    def test_single_variant(self):
        command = RandomVariantCommand(gen_variant(["one"]))

        prompts = list(command.prompts())

        assert len(prompts) == 1
        assert prompts[0] == "one"

    def test_multiple_variant(self):
        variants = gen_variant(["one", "two", "three"])
        command = RandomVariantCommand(variants)
        command._random = mock.Mock()
        random_choices = [
            [to_seqlit("one")],
            [to_seqlit("three")],
            [to_seqlit("two")],
            [to_seqlit("one")],
        ]
        command._random.choices.side_effect = random_choices

        for c in random_choices:
            prompts = list(command.prompts())
            assert len(prompts) == 1
            assert prompts[0] == c[0][0]

    def test_variant_with_literal(self):
        variants = gen_variant(["one", "two", "three"])
        command1 = RandomVariantCommand(variants)
        command2 = LiteralCommand(" ")
        command3 = LiteralCommand("circles")
        sequence = RandomSequenceCommand([command1, command2, command3])
        command1._random = mock.Mock()

        random_choices = [
            [to_seqlit("one")],
            [to_seqlit("three")],
            [to_seqlit("two")],
            [to_seqlit("one")],
        ]
        command1._random.choices.side_effect = random_choices
        for c in random_choices:
            prompts = list(sequence.prompts())
            assert len(prompts) == 1
            assert prompts[0] == f"{c[0][0]} circles"

    def test_variant_with_bound(self):
        variant_values = ["one", "two", "three"]
        variants = gen_variant(variant_values)
        variant_literals = [to_seqlit(v) for v in variant_values]

        command1 = RandomVariantCommand(variants, min_bound=1, max_bound=2)
        command1._random = mock.Mock()

        random_choices = [
            [to_seqlit("one")],
            [to_seqlit("two"), to_seqlit("one")],
            [to_seqlit("three")],
            [to_seqlit("three"), to_seqlit("one")],
        ]
        command1._random.choices.side_effect = random_choices
        command1._random.randint.side_effect = [1, 2, 1, 2]

        prompts = list(command1.prompts())
        assert len(prompts) == 1
        assert prompts[0] == "one"
        command1._random.choices.assert_called_with(
            variant_literals,
            weights=[1, 1, 1],
            k=1,
        )

        prompts = list(command1.prompts())
        assert prompts[0] == "two,one"
        command1._random.choices.assert_called_with(
            variant_literals,
            weights=[1, 1, 1],
            k=2,
        )

        prompts = list(command1.prompts())
        assert prompts[0] == "three"
        command1._random.choices.assert_called_with(
            variant_literals,
            weights=[1, 1, 1],
            k=1,
        )

        prompts = list(command1.prompts())
        assert prompts[0] == "three,one"
        command1._random.choices.assert_called_with(
            variant_literals,
            weights=[1, 1, 1],
            k=2,
        )

    def test_variant_with_bound_and_sep(self):
        variant_values = ["one", "two", "three"]
        variants = gen_variant(variant_values)
        variant_literals = [to_seqlit(v) for v in variant_values]

        command1 = RandomVariantCommand(variants, min_bound=1, max_bound=2, sep=" and ")
        command1._random = mock.Mock()

        random_choices = [to_seqlit("two"), to_seqlit("one")]
        command1._random.choices.return_value = random_choices
        command1._random.randint.side_effect = [2]

        prompts = list(command1.prompts())
        assert len(prompts) == 1
        assert prompts[0] == "two and one"
        command1._random.choices.assert_called_with(
            variant_literals,
            weights=[1, 1, 1],
            k=2,
        )

    def test_two_variants(self):
        variants1 = gen_variant(["red", "green"])
        variants2 = gen_variant(["circles", "squares", "triangles"])

        command1 = RandomVariantCommand(variants1)
        command1._random = mock.Mock()
        command2 = LiteralCommand(" ")
        command3 = RandomVariantCommand(variants2)
        command3._random = mock.Mock()
        sequence = RandomSequenceCommand([command1, command2, command3])

        command1._random.choices.side_effect = [
            [to_seqlit("red")],
            [to_seqlit("green")],
        ]
        command3._random.choices.side_effect = [
            [to_seqlit("squares")],
            [to_seqlit("triangles")],
        ]
        assert sequence.get_prompt() == "red squares"
        assert sequence.get_prompt() == "green triangles"

    def test_varied_prompt(self):
        variants1 = gen_variant(["red", "green"])
        variants2 = gen_variant(["circles", "squares", "triangles"])

        command1 = RandomVariantCommand(variants1)
        command1._random = mock.Mock()
        command2 = LiteralCommand(" ")
        command3 = RandomVariantCommand(variants2)
        command3._random = mock.Mock()
        command4 = LiteralCommand(" ")
        command5 = LiteralCommand("are")
        command6 = LiteralCommand(" ")
        command7 = LiteralCommand("cool")
        sequence = RandomSequenceCommand(
            [command1, command2, command3, command4, command5, command6, command7],
        )

        command1._random.choices.side_effect = [
            [to_seqlit("red")],
            [to_seqlit("green")],
        ]

        command3._random.choices.side_effect = [
            [to_seqlit("squares")],
            [to_seqlit("triangles")],
        ]

        assert sequence.get_prompt() == "red squares are cool"
        assert sequence.get_prompt() == "green triangles are cool"


class TestWildcardsCommand:
    def test_basic_wildcard(self, builder: RandomActionBuilder):
        command = builder.get_wildcard_action("colours")
        command = cast(RandomWildcardCommand, command)
        command._random = mock.Mock()

        with mock.patch.object(
            builder._wildcard_manager,
            "get_all_values",
            return_value=["red", "green", "blue"],
        ):
            command = cast(RandomWildcardCommand, command)
            command._random.choice.side_effect = ["green"]

            prompts = list(command.prompts())
            assert len(prompts) == 1
            assert prompts[0] == "green"

    def test_wildcard_with_literal(self, builder: RandomActionBuilder):
        command1 = builder.get_wildcard_action("colours")
        command1 = cast(RandomWildcardCommand, command1)
        command1._random = mock.Mock()
        space = builder.get_literal_action(" ")
        command2 = builder.get_literal_action("are")
        command3 = builder.get_literal_action("cool")
        sequence = builder.get_sequence_action(
            [command1, space, command2, space, command3],
        )

        with mock.patch.object(
            builder._wildcard_manager,
            "get_all_values",
            return_value=["red", "green", "blue"],
        ):

            random_choices = ["green", "red"]
            command1._random.choice.side_effect = random_choices

            for c in random_choices:
                assert sequence.get_prompt() == f"{c} are cool"

    def test_wildcard_with_variant(self, builder: RandomActionBuilder):
        command1 = builder.get_wildcard_action("colours")
        command1 = cast(RandomWildcardCommand, command1)
        command1._random = mock.Mock()

        space = builder.get_literal_action(" ")
        command3 = RandomVariantCommand(gen_variant(["circles", "squares"]))
        command3._random = mock.Mock()
        sequence = builder.get_sequence_action([command1, space, command3])

        with mock.patch.object(
            builder._wildcard_manager,
            "get_all_values",
            return_value=["red", "green", "blue"],
        ):

            command1._random.choice.side_effect = ["red", "blue"]
            command3._random.choices.side_effect = [
                [to_seqlit("circles")],
                [to_seqlit("squares")],
            ]

            assert sequence.get_prompt() == "red circles"
            assert sequence.get_prompt() == "blue squares"


class TestRandomGenerator:
    def test_empty(self, generator: RandomGenerator):
        prompts = generator.generate_prompts("", 5)
        assert len(prompts) == 0

    def test_literals(self, generator: RandomGenerator):
        prompts = generator.generate_prompts("A literal sentence", 5)
        assert len(prompts) == 5

        for p in prompts:
            assert p == "A literal sentence"

    def test_literal_with_square_brackets(self, generator: RandomGenerator):
        prompts = generator.generate_prompts("Test [low emphasis]", 1)
        assert len(prompts) == 1
        assert prompts[0] == "Test [low emphasis]"

    def test_variants(self, generator: RandomGenerator):
        with mock.patch(
            "dynamicprompts.parser.random_generator.random.choices",
        ) as mock_random:
            random_choices = [
                [to_seqlit("square")],
                [to_seqlit("square")],
                [to_seqlit("circle")],
                [to_seqlit("square")],
                [to_seqlit("circle")],
            ]
            mock_random.side_effect = random_choices
            prompts = generator.generate_prompts("A red {square|circle}", 5)

            assert len(prompts) == 5
            for prompt, choice in zip(prompts, random_choices):
                assert prompt == f"A red {choice[0][0]}"

    def test_variant_with_blank(self, generator: RandomGenerator):
        generator._random = mock.Mock()
        generator._random.choices.side_effect = [
            [RandomSequenceCommand([])],
            [to_seqlit("red")],
            [to_seqlit("blue")],
        ]
        prompts = generator.generate_prompts("A {|red|blue} rose", 3)

        assert len(prompts) == 3
        assert prompts[0] == "A  rose"
        assert prompts[1] == "A red rose"
        assert prompts[2] == "A blue rose"

    def test_variants_with_bounds(self, generator: RandomGenerator):
        generator._random = mock.Mock()
        shapes = [to_seqlit("square"), to_seqlit("circle")]

        generator._random.randint.return_value = 2
        generator._random.choices.side_effect = [shapes]
        prompts = generator.generate_prompts("A red {2$$square|circle}", 1)

        assert len(prompts) == 1
        assert prompts[0] == "A red square,circle"

    def test_variants_with_larger_bounds_than_choices(self, generator: RandomGenerator):
        generator._random = mock.Mock()
        shapes = [to_seqlit("square"), to_seqlit("circle")]
        generator._random.randint.return_value = 3
        generator._random.choices.side_effect = [shapes]
        prompts = generator.generate_prompts("A red {3$$square|circle}", 1)

        assert len(prompts) == 1
        assert prompts[0] == "A red square,circle"

    def test_variants_with_pipe_separator(self, generator: RandomGenerator):
        generator._random = mock.Mock()
        shapes = [to_seqlit("square"), to_seqlit("circle")]
        generator._random.randint.return_value = 3
        generator._random.choices.side_effect = [shapes]
        prompts = generator.generate_prompts("A red {3$$|$$square|circle}", 1)

        assert len(prompts) == 1
        assert prompts[0] == "A red square|circle"
        print(prompts[0])

    def test_two_variants(self, generator: RandomGenerator):
        with mock.patch(
            "dynamicprompts.parser.random_generator.random.choices",
        ) as mock_random:
            mock_random.side_effect = [
                [to_seqlit("green")],
                [to_seqlit("square")],
                [to_seqlit("green")],
                [to_seqlit("circle")],
            ]
            prompts = generator.generate_prompts("A {red|green} {square|circle}", 2)
            assert len(prompts) == 2
            assert prompts[0] == "A green square"
            assert prompts[1] == "A green circle"

    def test_weighted_variant(self, generator: RandomGenerator):
        generator._random = mock.Mock()

        generator._random.choices.return_value = [to_seqlit("green")]
        generator._random.randint.return_value = 1
        prompts = generator.generate_prompts("A {1::red|2::green|3::blue}", 1)

        assert len(prompts) == 1
        assert prompts[0] == "A green"

    def test_wildcards(self, generator: RandomGenerator):
        generator._random = mock.Mock()
        with mock.patch.object(
            generator._wildcard_manager,
            "get_all_values",
            return_value=to_seqlit("red", "green", "blue"),
        ):
            generator._random.choice.side_effect = ["red", "green"]
            generator._random.choices.side_effect = [
                [to_seqlit("square")],
                [to_seqlit("circle")],
            ]
            prompts = generator.generate_prompts("A __colours__ {square|circle}", 2)
            assert len(prompts) == 2
            assert prompts[0] == "A red square"
            assert prompts[1] == "A green circle"

    def test_missing_wildcard(self, generator: RandomGenerator):
        with mock.patch.object(
            generator._wildcard_manager,
            "get_all_values",
            return_value=[],
        ):
            prompts = generator.generate_prompts("A __missing__ wildcard", 1)
            assert len(prompts) == 1
            assert prompts[0] == "A __missing__ wildcard"

    def test_nospace_before_or_after_wildcard(self, generator: RandomGenerator):
        generator._random = mock.Mock()
        with mock.patch.object(
            generator._wildcard_manager,
            "get_all_values",
            return_value=to_seqlit("red", "green", "blue"),
        ):

            generator._random.choice.side_effect = ["red", "green"]
            prompts = generator.generate_prompts("(__colours__:2.3) ", 1)
            assert prompts[0] == "(red:2.3) "
