from unittest import mock

import pytest
from dynamicprompts.commands import (
    LiteralCommand,
    SamplingMethod,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.samplers.random import RandomSampler
from dynamicprompts.wildcardmanager import WildcardManager

from tests.consts import ONE_TWO_THREE, RED_AND_GREEN, RED_GREEN_BLUE, SHAPES


@pytest.fixture
def sampler(wildcard_manager: WildcardManager) -> RandomSampler:
    return RandomSampler(wildcard_manager=wildcard_manager)


class TestRandomSequenceCommand:
    def test_prompts(self, sampler: RandomSampler):
        sequence = SequenceCommand.from_literals(["one", " ", "two", " ", "three"])
        prompt = next(sampler.generator_from_command(sequence))
        assert prompt == "one two three"


class TestVariantCommand:
    def test_empty_variant(self, sampler: RandomSampler):
        command = VariantCommand([])
        prompts = list(sampler.generator_from_command(command))
        assert len(prompts) == 0

    def test_single_variant(self, sampler: RandomSampler):
        command = VariantCommand.from_literals_and_weights(["one"])
        prompt = next(sampler.generator_from_command(command))
        assert prompt == "one"

    def test_multiple_variant(self, sampler: RandomSampler):
        command = VariantCommand.from_literals_and_weights(ONE_TWO_THREE)
        sampler._random = mock.Mock()
        random_choices = [
            [LiteralCommand("one")],
            [LiteralCommand("three")],
            [LiteralCommand("two")],
            [LiteralCommand("one")],
        ]
        sampler._random.choices.side_effect = random_choices

        for c in random_choices:
            prompt = next(sampler.generator_from_command(command))
            assert prompt == c[0].literal

    def test_sampling_method(self, sampler: RandomSampler):
        command = VariantCommand.from_literals_and_weights(
            ONE_TWO_THREE,
            sampling_method=SamplingMethod.COMBINATORIAL,
        )
        sampler._random = mock.Mock()
        random_choices = [
            [LiteralCommand("one")],
            [LiteralCommand("three")],
            [LiteralCommand("two")],
            [LiteralCommand("one")],
        ]
        sampler._random.choices.side_effect = random_choices
        prompts = list(sampler.generate_prompts(command))
        assert prompts == ONE_TWO_THREE

        command = VariantCommand.from_literals_and_weights(
            ONE_TWO_THREE,
            sampling_method=SamplingMethod.RANDOM,
        )
        prompts = sampler.generate_prompts(command)
        for c in random_choices:
            prompt = next(sampler.generator_from_command(command))
            assert prompt == c[0].literal

    def test_variant_with_literal(self, sampler: RandomSampler):
        command1 = VariantCommand.from_literals_and_weights(ONE_TWO_THREE)
        command2 = LiteralCommand(" ")
        command3 = LiteralCommand("circles")
        sequence = SequenceCommand([command1, command2, command3])
        sampler._random = mock.Mock()

        random_choices = [
            [LiteralCommand("one")],
            [LiteralCommand("three")],
            [LiteralCommand("two")],
            [LiteralCommand("one")],
        ]
        sampler._random.choices.side_effect = random_choices
        for c in random_choices:
            prompt = next(sampler.generator_from_command(sequence))
            assert prompt == f"{c[0].literal} circles"

    def test_variant_with_bound(self, sampler: RandomSampler):
        variant_values = ONE_TWO_THREE
        command1 = VariantCommand.from_literals_and_weights(
            variant_values,
            min_bound=1,
            max_bound=2,
        )
        sampler._random = mock.Mock()

        random_choices = [
            [LiteralCommand("one")],
            [LiteralCommand("two"), LiteralCommand("one")],
            [LiteralCommand("three")],
            [LiteralCommand("three"), LiteralCommand("one")],
        ]
        sampler._random.choices.side_effect = random_choices
        sampler._random.randint.side_effect = [1, 2, 1, 2]

        gen = sampler.generator_from_command(command1)
        for c in random_choices:
            assert next(gen) == ",".join([v.literal for v in c])

    def test_variant_with_bound_and_sep(self, sampler: RandomSampler):
        command1 = VariantCommand.from_literals_and_weights(
            ONE_TWO_THREE,
            min_bound=1,
            max_bound=2,
            separator=" and ",
        )
        sampler._random = mock.Mock()

        random_choices = [LiteralCommand("two"), LiteralCommand("one")]
        sampler._random.choices.return_value = random_choices
        sampler._random.randint.side_effect = [2]

        prompt = next(sampler.generator_from_command(command1))
        assert prompt == "two and one"

    def test_two_variants(self, sampler: RandomSampler):
        command1 = VariantCommand.from_literals_and_weights(RED_AND_GREEN)
        command2 = LiteralCommand(" ")
        command3 = VariantCommand.from_literals_and_weights(SHAPES)
        sequence = SequenceCommand([command1, command2, command3])
        expected_combos = {
            f"{color} {shape}" for color in RED_AND_GREEN for shape in SHAPES
        }
        generated_combos = set()
        gen = sampler.generator_from_command(sequence)
        # This could technically loop forever if the underlying RNG is broken,
        # but we'll take our chances.
        while generated_combos != expected_combos:
            generated_combos.add(next(gen))

    def test_varied_prompt(self, sampler: RandomSampler):
        command1 = VariantCommand.from_literals_and_weights(RED_AND_GREEN)
        command3 = VariantCommand.from_literals_and_weights(SHAPES)
        sequence = SequenceCommand.from_literals(
            [command1, " ", command3, " ", "are", " ", "cool"],
        )

        sampler._random = mock.Mock()
        sampler._random.choices.side_effect = [
            [LiteralCommand("red")],
            [LiteralCommand("squares")],
            [LiteralCommand("green")],
            [LiteralCommand("triangles")],
        ]
        gen = sampler.generator_from_command(sequence)

        assert next(gen) == "red squares are cool"
        assert next(gen) == "green triangles are cool"


class TestWildcardsCommand:
    def test_basic_wildcard(self, sampler: RandomSampler):
        command = WildcardCommand("colors*")
        wildcard_colors = set(
            sampler._wildcard_manager.get_all_values(command.wildcard),
        )
        generated_values = set()
        gen = sampler.generator_from_command(command)
        # This could technically loop forever if the underlying RNG is broken,
        # but we'll take our chances.
        while generated_values != wildcard_colors:
            generated_values.add(next(gen))

    def test_sampling_method(self, sampler: RandomSampler):
        command = WildcardCommand(
            "colors*",
            sampling_method=SamplingMethod.COMBINATORIAL,
        )
        wildcard_colors = sampler._wildcard_manager.get_all_values(command.wildcard)
        gen = sampler.generator_from_command(command)

        assert list(gen) == list(wildcard_colors)

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

    def test_wildcard_with_literal(self, sampler: RandomSampler):
        command = WildcardCommand("colors*")
        sequence = SequenceCommand.from_literals(
            [command, " ", "are", " ", LiteralCommand("cool")],
        )
        wildcard_colors = set(
            sampler._wildcard_manager.get_all_values(command.wildcard),
        )
        generated_values = set()
        gen = sampler.generator_from_command(sequence)
        # This could technically loop forever if the underlying RNG is broken,
        # but we'll take our chances.
        while len(generated_values) < len(wildcard_colors):
            prompt = next(gen)
            color, _, rest = prompt.partition(" ")
            assert color in wildcard_colors
            assert rest == "are cool"
            generated_values.add(prompt)

    def test_wildcard_with_variant(self, sampler: RandomSampler):
        command1 = WildcardCommand("colors*")
        wildcard_colors = set(
            sampler._wildcard_manager.get_all_values(command1.wildcard),
        )
        total_count = len(wildcard_colors) * len(SHAPES)
        command3 = VariantCommand.from_literals_and_weights(SHAPES)
        command3._random = mock.Mock()
        sequence = SequenceCommand.from_literals([command1, " ", command3])
        generated_values = set()
        gen = sampler.generator_from_command(sequence)
        # This could technically loop forever if the underlying RNG is broken,
        # but we'll take our chances.
        while len(generated_values) < total_count:
            prompt = next(gen)
            color, _, shape = prompt.partition(" ")
            assert color in wildcard_colors
            assert shape in SHAPES
            generated_values.add(prompt)


class TestRandomGenerator:
    def test_empty(self, sampler: RandomSampler):
        prompts = list(sampler.generate_prompts("", 5))
        assert len(prompts) == 0

    def test_literals(self, sampler: RandomSampler):
        sentence = "A literal sentence"
        assert list(sampler.generate_prompts(sentence, 5)) == [sentence] * 5

    def test_literal_with_square_brackets(self, sampler: RandomSampler):
        prompts = list(sampler.generate_prompts("Test [low emphasis]", 1))
        assert len(prompts) == 1
        assert prompts[0] == "Test [low emphasis]"

    def test_variants(self, sampler: RandomSampler):
        expected_prompts = {"A red square", "A red circle"}
        generated_prompts = set()
        while generated_prompts != expected_prompts:
            prompts = list(sampler.generate_prompts("A red {square|circle}", 5))
            assert len(prompts) == 5  # should generate 5 prompts when asked to
            assert all(p in expected_prompts for p in prompts)
            generated_prompts.update(prompts)

    def test_variant_with_blank(self, sampler: RandomSampler):
        expected_prompts = {"A  rose", "A red rose", "A blue rose"}
        generated_prompts = set()
        while generated_prompts != expected_prompts:
            prompts = list(sampler.generate_prompts("A {red|blue|} rose", 5))
            assert len(prompts) == 5
            assert all(p in expected_prompts for p in prompts)
            generated_prompts.update(prompts)

    def test_variants_with_bounds(self, sampler: RandomSampler):
        sampler._random = mock.Mock()
        shapes = [LiteralCommand("square"), LiteralCommand("circle")]

        sampler._random.randint.return_value = 2
        sampler._random.choices.side_effect = [shapes]
        assert list(sampler.generate_prompts("A red {2$$square|circle}", 1)) == [
            "A red square,circle",
        ]

    def test_variants_with_larger_bounds_than_choices(self, sampler: RandomSampler):
        sampler._random = mock.Mock()
        shapes = [LiteralCommand("square"), LiteralCommand("circle")]
        sampler._random.randint.return_value = 3
        sampler._random.choices.side_effect = [shapes]
        prompts = list(sampler.generate_prompts("A red {3$$square|circle}", 1))

        assert len(prompts) == 1
        assert prompts[0] == "A red square,circle"

    def test_variants_with_pipe_separator(self, sampler: RandomSampler):
        sampler._random = mock.Mock()
        shapes = [LiteralCommand("square"), LiteralCommand("circle")]
        sampler._random.randint.return_value = 3
        sampler._random.choices.side_effect = [shapes]
        assert list(sampler.generate_prompts("A red {3$$|$$square|circle}", 1)) == [
            "A red square|circle",
        ]

    def test_two_variants(self, sampler: RandomSampler):
        with mock.patch(
            "dynamicprompts.samplers.random.DEFAULT_RANDOM.choices",
        ) as mock_random:
            mock_random.side_effect = [
                [LiteralCommand("green")],
                [LiteralCommand("square")],
                [LiteralCommand("green")],
                [LiteralCommand("circle")],
            ]
            assert list(
                sampler.generate_prompts("A {red|green} {square|circle}", 2),
            ) == [
                "A green square",
                "A green circle",
            ]

    def test_weighted_variant(self, sampler: RandomSampler):
        sampler._random = mock.Mock()

        sampler._random.choices.return_value = [LiteralCommand("green")]
        sampler._random.randint.return_value = 1
        prompts = list(sampler.generate_prompts("A {1::red|2::green|3::blue}", 1))

        assert len(prompts) == 1
        assert prompts[0] == "A green"

    def test_wildcards(self, sampler: RandomSampler):
        sampler._random = mock.Mock()
        with mock.patch.object(
            sampler._wildcard_manager,
            "get_all_values",
            return_value=SequenceCommand.from_literals(RED_GREEN_BLUE),
        ):
            sampler._random.choice.side_effect = RED_AND_GREEN
            sampler._random.choices.side_effect = [
                [LiteralCommand("square")],
                [LiteralCommand("circle")],
            ]
            assert list(
                sampler.generate_prompts("A __colours__ {square|circle}", 2),
            ) == [
                "A red square",
                "A green circle",
            ]

    def test_missing_wildcard(self, sampler: RandomSampler):
        with mock.patch.object(
            sampler._wildcard_manager,
            "get_all_values",
            return_value=[],
        ):
            assert list(sampler.generate_prompts("A __missing__ wildcard", 1)) == [
                "A __missing__ wildcard",
            ]

    def test_nospace_before_or_after_wildcard(self, sampler: RandomSampler):
        sampler._random = mock.Mock()
        with mock.patch.object(
            sampler._wildcard_manager,
            "get_all_values",
            return_value=SequenceCommand.from_literals(RED_GREEN_BLUE),
        ):
            sampler._random.choice.side_effect = RED_AND_GREEN
            assert list(sampler.generate_prompts("(__colours__:2.3) ", 1)) == [
                "(red:2.3) ",
            ]
