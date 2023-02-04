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

from tests.consts import ONE_TWO_THREE, RED_AND_GREEN, RED_GREEN_BLUE, SHAPES

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


def test_literal(sampler: CyclicalSampler):
    literal = cyclical_literal("one")
    literal.sampling_method = SamplingMethod.CYCLICAL

    gen = sampler.generator_from_command(literal)
    _test_expected(["one"], gen)


class TestVariant:
    def test_empty_variant(self, sampler: CyclicalSampler):
        variant = variants_from_literals_and_weights([])
        assert variant.sampling_method == SamplingMethod.CYCLICAL

        gen = sampler.generator_from_command(variant)
        _test_expected([], gen)

    def test_single_variant(self, sampler: CyclicalSampler):
        variant = variants_from_literals_and_weights(
            ["one"],
            sampling_method=SamplingMethod.CYCLICAL,
        )

        gen = sampler.generator_from_command(variant)
        _test_expected(["one"], gen)

    def test_multiple_variant(self, sampler: CyclicalSampler):
        variant = variants_from_literals_and_weights(ONE_TWO_THREE)
        gen = sampler.generator_from_command(variant)
        _test_expected(ONE_TWO_THREE, gen)

    def test_variant_with_literal(self, sampler: CyclicalSampler):
        command1 = variants_from_literals_and_weights(ONE_TWO_THREE)
        command2 = cyclical_literal(" circles")
        sequence = cyclical_sequence([command1, command2])

        gen = sampler.generator_from_command(sequence)

        expected = [f"{val} circles" for val in ONE_TWO_THREE]
        _test_expected(expected, gen)

    def test_variant_with_zero_bound(self, sampler: CyclicalSampler):
        variant_values = ONE_TWO_THREE
        command1 = variants_from_literals_and_weights(
            variant_values,
            min_bound=0,
            max_bound=0,
        )

        gen = sampler.generator_from_command(command1)
        _test_expected([""], gen)

    def test_variant_with_bound(self, sampler: CyclicalSampler):
        variant_values = ONE_TWO_THREE
        command1 = variants_from_literals_and_weights(
            variant_values,
            min_bound=1,
            max_bound=2,
        )
        gen = sampler.generator_from_command(command1)
        expected = ONE_TWO_THREE + [
            f"{val1},{val2}"
            for val1 in ONE_TWO_THREE
            for val2 in ONE_TWO_THREE
            if val1 != val2
        ]

        _test_expected(expected, gen)

    def test_variant_with_bound_and_sep(self, sampler: CyclicalSampler):
        command1 = variants_from_literals_and_weights(
            ONE_TWO_THREE,
            min_bound=1,
            max_bound=2,
            separator=" and ",
        )

        gen = sampler.generator_from_command(command1)
        expected = ONE_TWO_THREE + [
            f"{val1} and {val2}"
            for val1 in ONE_TWO_THREE
            for val2 in ONE_TWO_THREE
            if val1 != val2
        ]

        _test_expected(expected, gen)

    def test_two_variants(self, sampler: CyclicalSampler):
        command1 = variants_from_literals_and_weights(RED_GREEN_BLUE)
        command2 = cyclical_literal(" ")
        command3 = variants_from_literals_and_weights(SHAPES)

        sequence = cyclical_sequence([command1, command2, command3])

        gen = sampler.generator_from_command(sequence)
        expected = [f"{color} {shape}" for color, shape in zip(RED_GREEN_BLUE, SHAPES)]

        _test_expected(expected, gen)

    def test_varied_prompt(self, sampler: CyclicalSampler):
        command1 = variants_from_literals_and_weights(RED_AND_GREEN)
        command3 = variants_from_literals_and_weights(SHAPES)

        sequence = sequence_from_literals(
            [command1, " ", command3, " ", "are", " ", "cool"],
        )

        gen = sampler.generator_from_command(sequence)
        expected = [
            "red circles are cool",
            "green squares are cool",
            "red triangles are cool",
            "green circles are cool",
            "red squares are cool",
            "green triangles are cool",
        ]

        _test_expected(expected, gen)


class TestWildcardsCommand:
    def test_basic_wildcard(self, sampler: CyclicalSampler):
        command = cyclical_wildcard("colors*")
        wildcard_colors = sampler._wildcard_manager.get_all_values(command.wildcard)

        gen = sampler.generator_from_command(command)
        _test_expected(wildcard_colors, gen)

    def test_wildcard_with_literal(self, sampler: CyclicalSampler):
        command = cyclical_wildcard("colors*")
        sequence = sequence_from_literals(
            [command, " ", "are", " ", cyclical_literal("cool")],
        )
        wildcard_colors = sampler._wildcard_manager.get_all_values(command.wildcard)

        gen = sampler.generator_from_command(sequence)
        expected = [f"{color} are cool" for color in wildcard_colors]

        _test_expected(expected, gen)

    def test_wildcard_with_variant(self, sampler: CyclicalSampler):
        command1 = cyclical_wildcard("colors*")
        command3 = variants_from_literals_and_weights(SHAPES)
        sequence = sequence_from_literals([command1, " ", command3])

        gen = sampler.generator_from_command(sequence)

        expected = [
            "blue circles",
            "green squares",
            "red triangles",
            "yellow circles",
            "blue squares",
            "green triangles",
            "red circles",
            "yellow squares",
            "blue triangles",
            "green circles",
            "red squares",
            "yellow triangles",
        ]

        _test_expected(expected, gen)


class TestCyclicalGenerator:
    def test_empty(self, sampler_manager: ConcreteSamplerManager):
        prompts = list(sampler_manager.sample_prompts("", 5))
        assert prompts == []

    def test_literals(self, sampler_manager: ConcreteSamplerManager):
        sentence = "A literal sentence"
        assert list(sampler_manager.sample_prompts(sentence, 5)) == [sentence] * 5

    def test_literal_with_square_brackets(
        self,
        sampler_manager: ConcreteSamplerManager,
    ):
        prompts = list(sampler_manager.sample_prompts("Test [low emphasis]", 1))
        assert len(prompts) == 1
        assert prompts[0] == "Test [low emphasis]"

    def test_variants(self, sampler_manager: ConcreteSamplerManager):
        template = "A red {square|circle}"
        expected_prompts = [
            "A red square",
            "A red circle",
            "A red square",
            "A red circle",
            "A red square",
        ]
        prompts = list(sampler_manager.sample_prompts(template, 5))

        assert prompts == expected_prompts

    def test_variant_with_blank(self, sampler_manager: ConcreteSamplerManager):
        template = "A {red|blue|} rose"
        expected_prompts = [
            "A red rose",
            "A blue rose",
            "A  rose",
            "A red rose",
            "A blue rose",
        ]

        prompts = list(sampler_manager.sample_prompts(template, 5))
        assert prompts == expected_prompts

    def test_variants_with_bounds(self, sampler_manager: ConcreteSamplerManager):
        template = "A red {2$$square|circle}"
        expected_prompts = [
            "A red square,circle",
            "A red circle,square",
            "A red square,circle",
            "A red circle,square",
            "A red square,circle",
        ]

        prompts = list(sampler_manager.sample_prompts(template, 5))
        assert prompts == expected_prompts

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

    def test_two_variants(self, sampler_manager: ConcreteSamplerManager):
        template = "A {red|green} {square|circle}"

        gen = list(sampler_manager.sample_prompts(template, 4))
        expected_prompts = [
            "A red square",
            "A green circle",
            "A red square",
            "A green circle",
        ]
        assert list(gen) == expected_prompts

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
