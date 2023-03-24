from __future__ import annotations

import random
from itertools import cycle, islice, zip_longest
from unittest.mock import patch

import pytest
from dynamicprompts.commands import (
    LiteralCommand,
    SequenceCommand,
    VariantCommand,
    VariantOption,
    WildcardCommand,
)
from dynamicprompts.samplers import CombinatorialSampler, CyclicalSampler, RandomSampler
from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.wildcards import WildcardManager
from pytest_lazyfixture import lazy_fixture

from tests.conftest import (
    sampling_context_lazy_fixtures,
)
from tests.consts import ONE_TWO_THREE, RED_AND_GREEN, RED_GREEN_BLUE, SHAPES
from tests.samplers.utils import (
    patch_random_sampler_variant_choices,
    patch_random_sampler_wildcard_choice,
)
from tests.utils import cross, zipstr

ONE_TWO_THREEx2 = cross(ONE_TWO_THREE, ONE_TWO_THREE)
ONE_TWO_THREEx2and = cross(ONE_TWO_THREE, ONE_TWO_THREE, sep=" and ")


@pytest.fixture
def data_lookups(wildcard_manager: WildcardManager) -> dict[str, list[str]]:
    wildcard_colours = wildcard_manager.get_all_values("colors*")
    shuffled_colours = wildcard_colours.copy()
    random.shuffle(shuffled_colours)
    cold_colours = wildcard_manager.get_all_values("colors-cold")
    shuffled_cold_colours = cold_colours.copy()

    return {
        "wildcard_colours": wildcard_colours,
        "wildcard_coloursx2": wildcard_colours * 2,
        "shuffled_colours": shuffled_colours,
        "cold_colours": cold_colours,
        "shuffled_cold_colours": shuffled_cold_colours,
    }


class TestSequenceCommand:
    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_prompts(self, sampling_context: SamplingContext):
        sequence = SequenceCommand.from_literals(["one", " ", "two", " ", "three"])
        prompt = next(sampling_context.generator_from_command(sequence))
        assert prompt == "one two three"

    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_custom_separator(self, sampling_context: SamplingContext):
        command1 = LiteralCommand("A")
        command2 = LiteralCommand("sentence")
        sequence = SequenceCommand([command1, command2], separator="|")
        prompt = next(sampling_context.generator_from_command(sequence))
        assert prompt == "A|sentence"


class TestLiteralCommand:
    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_single_literal(self, sampling_context: SamplingContext):
        literal = LiteralCommand("one")
        gen = sampling_context.generator_from_command(literal)
        assert next(gen) == "one"

    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_multiple_literals(
        self,
        sampling_context: SamplingContext,
    ):
        sequence = SequenceCommand.from_literals(["one", " ", "two", " ", "three"])
        prompts = sampling_context.generator_from_command(sequence)

        assert next(prompts) == "one two three"


class TestVariantCommand:
    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_empty_variant(self, sampling_context: SamplingContext):
        command = VariantCommand([])
        prompts = sampling_context.generator_from_command(command)
        assert len(list(prompts)) == 0

    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_single_variant(self, sampling_context: SamplingContext):
        command = VariantCommand.from_literals_and_weights(["one"])

        gen = sampling_context.generator_from_command(command)
        assert next(gen) == "one"

    @pytest.mark.parametrize(
        ("sampling_context", "expected"),
        [
            (lazy_fixture("random_sampling_context"), ["one", "three", "two", "one"]),
            (
                lazy_fixture("cyclical_sampling_context"),
                ["one", "two", "three", "one", "two"],
            ),
            (lazy_fixture("combinatorial_sampling_context"), ["one", "two", "three"]),
        ],
    )
    def test_multiple_variant(
        self,
        sampling_context: SamplingContext,
        expected: list[str],
    ):
        command = VariantCommand.from_literals_and_weights(ONE_TWO_THREE)
        sampler = sampling_context.default_sampler
        gen = sampling_context.generator_from_command(command)

        if isinstance(sampler, RandomSampler):
            with patch_random_sampler_variant_choices(
                [[LiteralCommand(e)] for e in expected],
            ):
                prompts = [next(gen) for _ in expected]
        else:
            prompts = [next(gen) for _ in expected]

        for prompt, e in zip(prompts, expected):
            assert prompt == e

    @pytest.mark.parametrize(
        ("sampling_context", "expected"),
        [
            (lazy_fixture("random_sampling_context"), ["three", "three", "one", "two"]),
            (
                lazy_fixture("cyclical_sampling_context"),
                ["one", "two", "three", "one", "two"],
            ),
            (lazy_fixture("combinatorial_sampling_context"), ["one", "two", "three"]),
        ],
    )
    def test_variant_with_literal(
        self,
        sampling_context: SamplingContext,
        expected: list[str],
    ):
        sampler = sampling_context.default_sampler

        command1 = VariantCommand.from_literals_and_weights(ONE_TWO_THREE)
        command2 = LiteralCommand(" circles")
        sequence = SequenceCommand([command1, command2])

        gen = sampling_context.generator_from_command(sequence)

        if isinstance(sampler, RandomSampler):
            with patch_random_sampler_variant_choices(
                [[LiteralCommand(e)] for e in expected],
            ):
                prompts = [next(gen) for _ in expected]
        else:
            prompts = [next(gen) for _ in expected]

        for prompt, e in zip(prompts, expected):
            assert prompt == f"{e} circles"

    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_variant_with_zero_bound(
        self,
        sampling_context: SamplingContext,
    ):
        command1 = VariantCommand.from_literals_and_weights(
            ONE_TWO_THREE,
            min_bound=0,
            max_bound=0,
        )

        gen = sampling_context.generator_from_command(command1)
        assert next(gen) == ""

    @pytest.mark.parametrize(
        ("sampling_context", "expected"),
        [
            (
                lazy_fixture("random_sampling_context"),
                ["three", "three,one", "one", "two,three"],
            ),
            (
                lazy_fixture("cyclical_sampling_context"),
                ONE_TWO_THREE + ONE_TWO_THREEx2 + ONE_TWO_THREE,
            ),
            (
                lazy_fixture("combinatorial_sampling_context"),
                ONE_TWO_THREE + ONE_TWO_THREEx2,
            ),
        ],
    )
    def test_variant_with_bound(
        self,
        sampling_context: SamplingContext,
        expected: list[str],
    ):
        sampler = sampling_context.default_sampler

        variant_values = ONE_TWO_THREE
        command1 = VariantCommand.from_literals_and_weights(
            variant_values,
            min_bound=1,
            max_bound=2,
        )
        gen = sampling_context.generator_from_command(command1)

        if isinstance(sampler, RandomSampler):
            random_choices = [
                [LiteralCommand(p) for p in e.split(",")] for e in expected
            ]
            with patch_random_sampler_variant_choices(random_choices):
                prompts = [next(gen) for _ in expected]
        else:
            prompts = [next(gen) for _ in expected]

        for prompt, e in zip(prompts, expected):
            assert prompt == e

    @pytest.mark.parametrize(
        ("sampling_context", "expected"),
        [
            (
                lazy_fixture("random_sampling_context"),
                ["three", "three and one", "one", "two and three"],
            ),
            (
                lazy_fixture("cyclical_sampling_context"),
                ONE_TWO_THREE + ONE_TWO_THREEx2and + ONE_TWO_THREE,
            ),
            (
                lazy_fixture("combinatorial_sampling_context"),
                ONE_TWO_THREE + ONE_TWO_THREEx2and,
            ),
        ],
    )
    def test_variant_with_bound_and_sep(
        self,
        sampling_context: SamplingContext,
        expected: list[str],
    ):
        sampler = sampling_context.default_sampler

        command1 = VariantCommand.from_literals_and_weights(
            ONE_TWO_THREE,
            min_bound=1,
            max_bound=2,
            separator=" and ",
        )

        gen = sampling_context.generator_from_command(command1)

        if isinstance(sampler, RandomSampler):
            random_choices = [
                [LiteralCommand(p) for p in e.split(" and ")] for e in expected
            ]
            with patch_random_sampler_variant_choices(random_choices):
                prompts = [next(gen) for _ in expected]
        else:
            prompts = [next(gen) for _ in expected]

        for prompt, e in zip(prompts, expected):
            assert prompt == e

    @pytest.mark.parametrize("separator", [",", " and "])
    @pytest.mark.parametrize(
        ("sampling_context", "key"),
        [
            (lazy_fixture("random_sampling_context"), "shuffled_colours"),
            (lazy_fixture("cyclical_sampling_context"), "wildcard_colours"),
            (lazy_fixture("combinatorial_sampling_context"), "wildcard_colours"),
        ],
    )
    def test_variant_with_wildcard(
        self,
        separator,
        sampling_context: SamplingContext,
        key: str,
        data_lookups: dict[str, list[str]],
    ):
        wildcard_command = WildcardCommand("colors*")
        variant_command = VariantCommand(
            [VariantOption(wildcard_command)],
            min_bound=2,
            max_bound=2,
            separator=separator,
        )

        gen = sampling_context.generator_from_command(variant_command)
        colors = [LiteralCommand(val) for val in data_lookups[key]]

        if isinstance(sampling_context.default_sampler, RandomSampler):
            color_pairs = [list(t) for t in zip(colors[::2], colors[1::2])]
            with patch_random_sampler_variant_choices(color_pairs):
                prompts = [next(gen) for _ in range(len(color_pairs))]
        elif isinstance(sampling_context.default_sampler, CombinatorialSampler):
            color_pairs = [[c1, c2] for c1 in colors for c2 in colors if c1 != c2]
            prompts = [next(gen) for _ in range(len(color_pairs))]
        elif isinstance(sampling_context.default_sampler, CyclicalSampler):
            color_pairs = [[c1, c2] for c1 in colors for c2 in colors if c1 != c2] * 2
            prompts = [next(gen) for _ in range(len(color_pairs))]
        else:
            raise NotImplementedError(
                f"Unknown sampler type {type(sampling_context.default_sampler)}",
            )

        color_pair_strings = [
            f"{c1.literal}{separator}{c2.literal}" for c1, c2 in color_pairs
        ]
        assert prompts == color_pair_strings

    @pytest.mark.parametrize(
        ("sampling_context", "key"),
        [
            (lazy_fixture("random_sampling_context"), "shuffled_cold_colours"),
            (lazy_fixture("cyclical_sampling_context"), "cold_colours"),
            (lazy_fixture("combinatorial_sampling_context"), "cold_colours"),
        ],
    )
    def test_variant_with_wildcard_and_high_bounds(
        self,
        sampling_context: SamplingContext,
        key: str,
        data_lookups: dict[str, list[str]],
    ):
        wildcard_command = WildcardCommand("colors-cold")
        separator = ","
        variant_command = VariantCommand(
            [VariantOption(wildcard_command)],
            min_bound=3,
            max_bound=3,
            separator=separator,
        )

        gen = sampling_context.generator_from_command(variant_command)
        colors = [LiteralCommand(val) for val in data_lookups[key]]

        if isinstance(sampling_context.default_sampler, RandomSampler):
            color_pairs = [list(t) for t in zip(colors[::2], colors[1::2])]
            with patch_random_sampler_variant_choices(color_pairs):
                prompts = [next(gen) for _ in range(len(color_pairs))]
        elif isinstance(sampling_context.default_sampler, CombinatorialSampler):
            color_pairs = [[c1, c2] for c1 in colors for c2 in colors if c1 != c2]
            prompts = [next(gen) for _ in range(len(color_pairs))]
        elif isinstance(sampling_context.default_sampler, CyclicalSampler):
            color_pairs = [[c1, c2] for c1 in colors for c2 in colors if c1 != c2] * 2
            prompts = [next(gen) for _ in range(len(color_pairs))]

        color_pair_strings = [
            f"{c1.literal}{separator}{c2.literal}" for c1, c2 in color_pairs
        ]
        assert prompts == color_pair_strings

    @pytest.mark.parametrize(
        ("sampling_context", "expected"),
        [
            (lazy_fixture("random_sampling_context"), ["red triangle", "blue circle"]),
            (
                lazy_fixture("cyclical_sampling_context"),
                zipstr(RED_GREEN_BLUE, SHAPES, sep=" "),
            ),
            (
                lazy_fixture("combinatorial_sampling_context"),
                cross(RED_GREEN_BLUE, SHAPES, sep=" "),
            ),
        ],
    )
    def test_two_variants(
        self,
        sampling_context: SamplingContext,
        expected: list[str],
    ):
        sampler = sampling_context.default_sampler

        command1 = VariantCommand.from_literals_and_weights(RED_GREEN_BLUE)
        command2 = LiteralCommand(" ")
        command3 = VariantCommand.from_literals_and_weights(SHAPES)

        sequence = SequenceCommand([command1, command2, command3])

        gen = sampling_context.generator_from_command(sequence)

        if isinstance(sampler, RandomSampler):
            random_choices = []
            for e in expected:
                parts = e.split(" ")
                random_choices += [[LiteralCommand(p)] for p in parts]

            with patch_random_sampler_variant_choices(random_choices):
                prompts = [next(gen) for _ in expected]
        else:
            prompts = [next(gen) for _ in expected]

        for prompt, e in zip(prompts, expected):
            assert prompt == e

    @pytest.mark.parametrize(
        ("sampling_context", "expected"),
        [
            (lazy_fixture("random_sampling_context"), ["red triangle", "blue circle"]),
            (
                lazy_fixture("cyclical_sampling_context"),
                zipstr(RED_AND_GREEN, SHAPES, sep=" "),
            ),
            (
                lazy_fixture("combinatorial_sampling_context"),
                cross(RED_AND_GREEN, SHAPES, sep=" "),
            ),
        ],
    )
    def test_varied_prompt(
        self,
        sampling_context: SamplingContext,
        expected: list[str],
    ):
        sampler = sampling_context.default_sampler

        command1 = VariantCommand.from_literals_and_weights(RED_AND_GREEN)
        command3 = VariantCommand.from_literals_and_weights(SHAPES)

        sequence = SequenceCommand(
            [
                command1,
                LiteralCommand(" "),
                command3,
                LiteralCommand(" "),
                LiteralCommand("are"),
                LiteralCommand(" "),
                LiteralCommand("cool"),
            ],
        )

        gen = sampling_context.generator_from_command(sequence)

        if isinstance(sampler, RandomSampler):
            random_choices = []
            for e in expected:
                parts = e.split(" ")
                random_choices += [[LiteralCommand(p)] for p in parts]

            with patch_random_sampler_variant_choices(random_choices):
                prompts = [next(gen) for _ in expected]
        else:
            prompts = [next(gen) for _ in expected]

        for prompt, e in zip(prompts, expected):
            assert prompt == f"{e} are cool"


class TestWildcardsCommand:
    @pytest.mark.parametrize(
        ("sampling_context", "key"),
        [
            (lazy_fixture("random_sampling_context"), "shuffled_colours"),
            (lazy_fixture("cyclical_sampling_context"), "wildcard_coloursx2"),
            (lazy_fixture("combinatorial_sampling_context"), "wildcard_colours"),
        ],
    )
    def test_basic_wildcard(
        self,
        sampling_context: SamplingContext,
        key: str,
        data_lookups: dict[str, list[str]],
    ):
        command = WildcardCommand("colors*")

        gen = sampling_context.generator_from_command(command)

        with patch_random_sampler_wildcard_choice(data_lookups[key]):
            prompts = [next(gen) for _ in range(len(data_lookups[key]))]

        for prompt, e in zip(prompts, data_lookups[key]):
            assert prompt == e

    @pytest.mark.parametrize(
        ("sampling_context", "key"),
        [
            (lazy_fixture("random_sampling_context"), "shuffled_colours"),
            (lazy_fixture("cyclical_sampling_context"), "wildcard_coloursx2"),
            (lazy_fixture("combinatorial_sampling_context"), "wildcard_colours"),
        ],
    )
    def test_wildcard_with_literal(
        self,
        sampling_context: SamplingContext,
        key: str,
        data_lookups: dict[str, list[str]],
    ):
        command = WildcardCommand("colors*")
        sequence = SequenceCommand.from_literals(
            [command, " ", "are", " ", LiteralCommand("cool")],
        )

        gen = sampling_context.generator_from_command(sequence)

        with patch_random_sampler_wildcard_choice(data_lookups[key]):
            prompts = [next(gen) for _ in range(len(data_lookups[key]))]

        for prompt, e in zip(prompts, data_lookups[key]):
            assert prompt == f"{e} are cool"

    @pytest.mark.parametrize(
        ("sampling_context", "key"),
        [
            (lazy_fixture("random_sampling_context"), "shuffled_colours"),
            (lazy_fixture("cyclical_sampling_context"), "wildcard_colours"),
            (lazy_fixture("combinatorial_sampling_context"), "wildcard_colours"),
        ],
    )
    def test_wildcard_with_variant(
        self,
        sampling_context: SamplingContext,
        key: str,
        data_lookups: dict[str, list[str]],
    ):
        sampler = sampling_context.default_sampler

        command1 = WildcardCommand("colors*")
        command3 = VariantCommand.from_literals_and_weights(SHAPES)
        sequence = SequenceCommand.from_literals([command1, " ", command3])

        gen = sampling_context.generator_from_command(sequence)

        if isinstance(sampler, RandomSampler):
            shuffled_colours = data_lookups[key]
            shuffled_shapes = SHAPES.copy()
            random.shuffle(shuffled_shapes)
            with patch_random_sampler_wildcard_choice(shuffled_colours):
                with patch_random_sampler_variant_choices(
                    [[LiteralCommand(shape)] for shape in shuffled_shapes],
                ):
                    expected = [
                        f"{c} {s}" for c, s in zip(shuffled_colours, shuffled_shapes)
                    ]
                    prompts = [next(gen) for _ in range(len(expected))]

        elif isinstance(sampler, CyclicalSampler):
            l1 = cycle(data_lookups[key])
            l2 = cycle(SHAPES)
            pairs = zip_longest(l1, l2)

            expected = [f"{e1} {e2}" for (e1, e2) in islice(pairs, 10)]
            prompts = [next(gen) for _ in range(len(expected))]

        elif isinstance(sampler, CombinatorialSampler):
            expected = cross(data_lookups[key], SHAPES, sep=" ")
            prompts = [next(gen) for _ in range(len(expected))]
        else:
            raise ValueError("Invalid sampler")

        for prompt, e in zip(prompts, expected):
            assert prompt == e

    @pytest.mark.parametrize(
        ("sampling_context", "expected"),
        [
            # (lazy_fixture("random_sampling_context"), ""),
            (
                lazy_fixture("cyclical_sampling_context"),
                ["red", "green", "blue", "pink", "green", "blue"],
            ),
            (
                lazy_fixture("combinatorial_sampling_context"),
                ["red", "pink", "green", "blue"],
            ),
        ],
    )
    def test_variant_nested_in_wildcard(
        self,
        sampling_context: SamplingContext,
        expected: list[str],
    ):
        with patch.object(
            sampling_context.wildcard_manager,
            "get_all_values",
            return_value=["{red|pink}", "green", "blue"],
        ):
            wildcard_command = WildcardCommand("colours")
            sequence = SequenceCommand([wildcard_command])

            gen = sampling_context.generator_from_command(sequence)

            prompts = [next(gen) for _ in range(len(expected))]

            assert prompts == expected

    @pytest.mark.parametrize(
        ("sampling_context", "expected"),
        [
            (lazy_fixture("random_sampling_context"), []),  # TODO fix this
            (
                lazy_fixture("cyclical_sampling_context"),
                [
                    "blue",
                    "red",
                    "green",
                    "yellow",
                    "blue",
                    "red",
                    "green",
                    "yellow",
                    "blue",
                ],
            ),
            (
                lazy_fixture("combinatorial_sampling_context"),
                ["blue", "green", "red", "yellow"],
            ),
        ],
    )
    def test_wildcard_nested_in_wildcard(
        self,
        sampling_context: SamplingContext,
        expected: list[str],
    ):
        wildcard_command = WildcardCommand("referencing-colors")
        sequence = SequenceCommand([wildcard_command])
        gen = sampling_context.generator_from_command(sequence)
        assert list(islice(gen, len(expected))) == expected
