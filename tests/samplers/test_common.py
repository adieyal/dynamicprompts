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
from dynamicprompts.enums import SamplingMethod
from dynamicprompts.parser.parse import parse
from dynamicprompts.samplers import CombinatorialSampler, CyclicalSampler, RandomSampler
from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.wildcards import WildcardManager
from dynamicprompts.wildcards.values import WildcardValues
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
def data_lookups(wildcard_manager: WildcardManager) -> dict[str, WildcardValues]:
    wildcard_colours = wildcard_manager.get_values("colors*")
    shuffled_colours = wildcard_colours.shuffled()
    cold_colours = wildcard_manager.get_values("colors-cold")
    shuffled_cold_colours = cold_colours.copy()

    return {
        "wildcard_colours": wildcard_colours,
        "wildcard_coloursx2": wildcard_colours + wildcard_colours,
        "shuffled_colours": shuffled_colours,
        "cold_colours": cold_colours,
        "shuffled_cold_colours": shuffled_cold_colours,
    }


class TestSequenceCommand:
    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_prompts(self, sampling_context: SamplingContext):
        sequence = SequenceCommand.from_literals(["one", " ", "two", " ", "three"])
        prompt = next(sampling_context.generator_from_command(sequence))
        assert str(prompt) == "one two three"

    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_custom_separator(self, sampling_context: SamplingContext):
        command1 = LiteralCommand("A")
        command2 = LiteralCommand("sentence")
        sequence = SequenceCommand([command1, command2], separator="|")
        prompt = next(sampling_context.generator_from_command(sequence))
        assert str(prompt) == "A|sentence"


class TestLiteralCommand:
    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_single_literal(self, sampling_context: SamplingContext):
        literal = LiteralCommand("one")
        gen = sampling_context.generator_from_command(literal)
        assert str(next(gen)) == "one"

    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_multiple_literals(
        self,
        sampling_context: SamplingContext,
    ):
        sequence = SequenceCommand.from_literals(["one", " ", "two", " ", "three"])
        prompts = sampling_context.generator_from_command(sequence)

        assert str(next(prompts)) == "one two three"


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
        assert str(next(gen)) == "one"

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
            assert str(prompt) == e

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
            assert str(prompt) == f"{e} circles"

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
        assert str(next(gen)) == ""

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
            assert str(prompt) == e

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
            assert str(prompt) == e

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
        assert [str(p) for p in prompts] == color_pair_strings

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
        assert [str(p) for p in prompts] == color_pair_strings

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
            assert str(prompt) == e

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
            assert str(prompt) == f"{e} are cool"


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
        data_lookups: dict[str, WildcardValues],
    ):
        command = WildcardCommand("colors*")

        gen = sampling_context.generator_from_command(command)

        values = data_lookups[key].string_values
        with patch_random_sampler_wildcard_choice(values):
            prompts = [next(gen) for _ in range(len(values))]

        for prompt, e in zip(prompts, values):
            assert str(prompt) == e

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
        data_lookups: dict[str, WildcardValues],
    ):
        command = WildcardCommand("colors*")
        sequence = SequenceCommand.from_literals(
            [command, " ", "are", " ", LiteralCommand("cool")],
        )

        gen = sampling_context.generator_from_command(sequence)
        values = data_lookups[key].string_values
        with patch_random_sampler_wildcard_choice(values):
            prompts = [next(gen) for _ in range(len(values))]

        with patch_random_sampler_wildcard_choice(values):
            for prompt, e in zip(prompts, values):
                assert str(prompt) == f"{e} are cool"

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
            shuffled_colours = data_lookups[key].string_values
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
            assert str(prompt) == e

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
            "get_values",
            return_value=WildcardValues.from_items(["{red|pink}", "green", "blue"]),
        ):
            wildcard_command = WildcardCommand("colours")
            sequence = SequenceCommand([wildcard_command])

            gen = sampling_context.generator_from_command(sequence)

            prompts = [next(gen) for _ in range(len(expected))]

            assert [str(p) for p in prompts] == expected

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
        ps = [str(p) for p in islice(gen, len(expected))]
        assert ps == expected

    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_wildcard_with_nested_variable(self, sampling_context: SamplingContext):
        cmd = parse("${temp=cold}wearing __colors-${temp}__ suede shoes")
        resolved_value = str(next(sampling_context.generator_from_command(cmd)))
        if isinstance(sampling_context.default_sampler, RandomSampler):
            assert resolved_value in (
                "wearing blue suede shoes",
                "wearing green suede shoes",
            )
        else:
            assert resolved_value == "wearing blue suede shoes"

    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_wildcard_with_default_variable(self, sampling_context: SamplingContext):
        cmd = parse("wearing __colors-${temp:cold}__ suede shoes")
        resolved_value = str(next(sampling_context.generator_from_command(cmd)))
        if isinstance(sampling_context.default_sampler, RandomSampler):
            assert resolved_value in (
                "wearing blue suede shoes",
                "wearing green suede shoes",
            )
        else:
            assert resolved_value == "wearing blue suede shoes"

    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_wildcard_with_undefined_variable(self, sampling_context: SamplingContext):
        cmd = parse("wearing __colors-${temp}__ suede shoes")
        resolved_value = str(next(sampling_context.generator_from_command(cmd)))
        assert (
            resolved_value
            == f"wearing {sampling_context.wildcard_manager.wildcard_wrap}colors-temp{sampling_context.wildcard_manager.wildcard_wrap} suede shoes"
        )

    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_wildcard_with_multiple_variables(self, sampling_context: SamplingContext):
        cmd = parse(
            "${genus=mammals}${species=feline}__animals/${genus:reptiles}/${species:snakes}__",
        )
        resolved_value = str(next(sampling_context.generator_from_command(cmd)))
        if isinstance(sampling_context.default_sampler, RandomSampler):
            assert resolved_value in ("cat", "tiger")
        else:
            assert resolved_value == "cat"

    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_wildcard_with_variable_and_glob(self, sampling_context: SamplingContext):
        cmd = parse("${genus=reptiles}__animals/${genus}/*__")
        resolved_value = str(next(sampling_context.generator_from_command(cmd)))
        if isinstance(sampling_context.default_sampler, RandomSampler):
            assert resolved_value in ("cobra", "gecko", "iguana", "python")
        else:
            assert resolved_value == "cobra"

    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_wildcard_with_variable_in_nested_wildcard(
        self,
        sampling_context: SamplingContext,
    ):
        cmd = parse("${genus=mammals}__animal__")
        resolved_value = str(next(sampling_context.generator_from_command(cmd)))
        if isinstance(sampling_context.default_sampler, RandomSampler):
            assert resolved_value in ("cat", "tiger", "dog", "wolf")
        else:
            assert resolved_value == "cat"

    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_nested_wildcard_with_parameterized_variable(
        self,
        sampling_context: SamplingContext,
    ):
        cmd = parse("__animal(genus=mammals)__")
        resolved_value = str(next(sampling_context.generator_from_command(cmd)))
        if isinstance(sampling_context.default_sampler, RandomSampler):
            assert resolved_value in ("cat", "tiger", "dog", "wolf")
        else:
            assert resolved_value == "cat"

    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_nested_wildcards_in_single_file(self, sampling_context: SamplingContext):
        cmd = parse(
            "${car=!{porsche|john_deere}}a __cars/${car}/types__ made by __cars/${car}/name__",
        )
        resolved_value = str(next(sampling_context.generator_from_command(cmd)))
        assert resolved_value in (
            "a sports car made by Porsche",
            "a tractor made by John Deere",
        )


class TestVariableCommands:
    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_variable_commands(self, sampling_context: SamplingContext):
        cmd = parse("${animal=cat}the animal is ${animal:dog}")
        assert (
            str(next(sampling_context.generator_from_command(cmd)))
            == "the animal is cat"
        )

    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_variable_commands_default(self, sampling_context: SamplingContext):
        cmd = parse("the animal is ${animal:dog}")
        assert (
            str(next(sampling_context.generator_from_command(cmd)))
            == "the animal is dog"
        )

    @pytest.mark.parametrize("immediate", [True, False])
    def test_immediate_variable_commands(
        self,
        random_sampling_context: SamplingContext,
        immediate: bool,
    ):
        prompt = "${number={1|2|3|4|5}}the number is ${number}"
        if immediate:
            prompt = prompt.replace("number=", "number=!")
        cmd = parse(prompt)
        gen = random_sampling_context.generator_from_command(cmd)
        seen = set(islice(gen, 40))
        if immediate:
            # Since the variable is immediately resolved, no matter how many times
            # we sample the random generator, we must get the same result
            assert len(seen) == 1
        else:
            # Otherwise we should've seen more than one result (but since it's a
            # random context, we can't guarantee that we'll see all 5)
            assert len(seen) > 1

    def test_immediate_literal_variable(self, random_sampling_context: SamplingContext):
        # Just a coverage test for the optimization for literal variables
        cmd = parse("${a =! foo}${a}")
        assert str(next(random_sampling_context.generator_from_command(cmd))) == "foo"

    @pytest.mark.parametrize(
        "prompt, possible_results",
        [
            (
                "${season=summer} ${temp=cold} ${location=north}__drink/beverage__",
                ("a glass of iced tea", "a glass of iced pop"),
            ),
            (
                "${season=summer} ${temp=cold} ${location=south}__drink/winter/beverage__",
                ("a mug of hot coffee"),
            ),
            (
                "${season=summer} ${temp=cold}__drink/winter/beverage__",
                ("a mug of hot tea"),
            ),
            (
                "__drink/summer/beverage__",
                ("a glass of iced sweet tea", "a glass of iced soda"),
            ),
            (
                "${location=north}__drink/summer/beverage__",
                ("a glass of iced tea", "a glass of iced pop"),
            ),
        ],
    )
    def test_preserve_variable(
        self,
        random_sampling_context: SamplingContext,
        prompt: str,
        possible_results: list[str],
    ):
        cmd = parse(prompt)
        resolved_value = str(
            next(random_sampling_context.generator_from_command(cmd)),
        ).strip()
        assert resolved_value in possible_results

    def test_unknown_variable(self, wildcard_manager: WildcardManager):
        ctx1 = SamplingContext(
            default_sampling_method=SamplingMethod.RANDOM,
            wildcard_manager=wildcard_manager,
        )
        ctx2 = SamplingContext(
            default_sampling_method=SamplingMethod.RANDOM,
            wildcard_manager=wildcard_manager,
            unknown_variable_value="oop!",
        )
        ctx3 = SamplingContext(
            default_sampling_method=SamplingMethod.RANDOM,
            wildcard_manager=wildcard_manager,
            unknown_variable_value=VariantCommand.from_literals_and_weights(["bloop!"]),
        )
        cmd = parse("${a}")
        with pytest.raises(KeyError):
            next(ctx1.generator_from_command(cmd))
        assert str(next(ctx2.generator_from_command(cmd))) == "oop!"
        assert str(next(ctx3.generator_from_command(cmd))) == "bloop!"
