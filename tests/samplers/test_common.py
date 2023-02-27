from __future__ import annotations

import random
from itertools import cycle, islice, zip_longest
from unittest.mock import patch

import pytest
from dynamicprompts.commands import (
    LiteralCommand,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.commands.base import SamplingMethod
from dynamicprompts.sampler_routers.concrete_sampler_router import ConcreteSamplerRouter
from dynamicprompts.samplers import CombinatorialSampler, CyclicalSampler, RandomSampler
from dynamicprompts.wildcardmanager import WildcardManager
from pytest import FixtureRequest
from pytest_lazyfixture import lazy_fixture

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

    return {
        "wildcard_colours": wildcard_colours,
        "wildcard_coloursx2": wildcard_colours * 2,
        "shuffled_colours": shuffled_colours,
    }


class TestSequenceCommand:
    @pytest.mark.parametrize(
        ("sampler_router", "expected"),
        [
            (lazy_fixture("random_sampler_router"), "one two three"),
            (lazy_fixture("cyclical_sampler_router"), "one two three"),
            (lazy_fixture("combinatorial_sampler_router"), "one two three"),
        ],
    )
    def test_prompts(
        self,
        sampler_router: ConcreteSamplerRouter,
        expected: str,
    ):
        sequence = SequenceCommand.from_literals(["one", " ", "two", " ", "three"])
        prompt = next(sampler_router.generator_from_command(sequence))
        assert prompt == expected

    @pytest.mark.parametrize(
        ("sampler_router", "expected"),
        [
            (lazy_fixture("random_sampler_router"), "A|sentence"),
            (lazy_fixture("cyclical_sampler_router"), "A|sentence"),
            (lazy_fixture("combinatorial_sampler_router"), "A|sentence"),
        ],
    )
    def test_custom_separator(
        self,
        sampler_router: ConcreteSamplerRouter,
        expected: str,
    ):
        command1 = LiteralCommand("A")
        command2 = LiteralCommand("sentence")
        sequence = SequenceCommand([command1, command2], separator="|")
        prompt = next(sampler_router.generator_from_command(sequence))
        assert prompt == expected


class TestLiteralCommand:
    @pytest.mark.parametrize(
        ("sampler_router", "expected"),
        [
            (lazy_fixture("random_sampler_router"), "one"),
            (lazy_fixture("cyclical_sampler_router"), "one"),
            (lazy_fixture("combinatorial_sampler_router"), "one"),
        ],
    )
    def test_single_literal(
        self,
        sampler_router: ConcreteSamplerRouter,
        expected: str,
        request: FixtureRequest,
    ):
        literal = LiteralCommand("one")
        gen = sampler_router.generator_from_command(literal)
        assert next(gen) == expected

    @pytest.mark.parametrize(
        ("sampler_router", "expected"),
        [
            (lazy_fixture("random_sampler_router"), "one two three"),
            (lazy_fixture("cyclical_sampler_router"), "one two three"),
            (lazy_fixture("combinatorial_sampler_router"), "one two three"),
        ],
    )
    def test_multiple_literals(
        self,
        sampler_router: ConcreteSamplerRouter,
        expected: str,
    ):
        sequence = SequenceCommand.from_literals(["one", " ", "two", " ", "three"])
        prompts = sampler_router.generator_from_command(sequence)

        assert next(prompts) == expected


class TestVariantCommand:
    @pytest.mark.parametrize(
        ("sampler_router"),
        [
            (lazy_fixture("random_sampler_router")),
            (lazy_fixture("cyclical_sampler_router")),
            (lazy_fixture("combinatorial_sampler_router")),
        ],
    )
    def test_empty_variant(self, sampler_router: ConcreteSamplerRouter):
        command = VariantCommand([])
        prompts = sampler_router.generator_from_command(command)
        assert len(list(prompts)) == 0

    @pytest.mark.parametrize(
        ("sampler_router", "expected"),
        [
            (lazy_fixture("random_sampler_router"), "one"),
            (lazy_fixture("cyclical_sampler_router"), "one"),
            (lazy_fixture("combinatorial_sampler_router"), "one"),
        ],
    )
    def test_single_variant(
        self,
        sampler_router: ConcreteSamplerRouter,
        expected: str,
    ):
        command = VariantCommand.from_literals_and_weights(["one"])

        gen = sampler_router.generator_from_command(command)
        assert next(gen) == expected

    @pytest.mark.parametrize(
        ("sampler_router", "expected"),
        [
            (lazy_fixture("random_sampler_router"), ["one", "three", "two", "one"]),
            (
                lazy_fixture("cyclical_sampler_router"),
                ["one", "two", "three", "one", "two"],
            ),
            (lazy_fixture("combinatorial_sampler_router"), ["one", "two", "three"]),
        ],
    )
    def test_multiple_variant(
        self,
        sampler_router: ConcreteSamplerRouter,
        expected: list[str],
    ):
        command = VariantCommand.from_literals_and_weights(ONE_TWO_THREE)
        sampler = sampler_router._samplers[SamplingMethod.DEFAULT]

        gen = sampler.generator_from_command(command)

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
        ("sampler_router", "expected"),
        [
            (lazy_fixture("random_sampler_router"), ["three", "three", "one", "two"]),
            (
                lazy_fixture("cyclical_sampler_router"),
                ["one", "two", "three", "one", "two"],
            ),
            (lazy_fixture("combinatorial_sampler_router"), ["one", "two", "three"]),
        ],
    )
    def test_variant_with_literal(
        self,
        sampler_router: ConcreteSamplerRouter,
        expected: list[str],
    ):
        sampler = sampler_router._samplers[SamplingMethod.DEFAULT]

        command1 = VariantCommand.from_literals_and_weights(ONE_TWO_THREE)
        command2 = LiteralCommand(" circles")
        sequence = SequenceCommand([command1, command2])

        gen = sampler_router.generator_from_command(sequence)

        if isinstance(sampler, RandomSampler):
            with patch_random_sampler_variant_choices(
                [[LiteralCommand(e)] for e in expected],
            ):
                prompts = [next(gen) for _ in expected]
        else:
            prompts = [next(gen) for _ in expected]

        for prompt, e in zip(prompts, expected):
            assert prompt == f"{e} circles"

    @pytest.mark.parametrize(
        ("sampler_router"),
        [
            (lazy_fixture("random_sampler_router")),
            (lazy_fixture("cyclical_sampler_router")),
            (lazy_fixture("combinatorial_sampler_router")),
        ],
    )
    def test_variant_with_zero_bound(
        self,
        sampler_router: ConcreteSamplerRouter,
    ):
        command1 = VariantCommand.from_literals_and_weights(
            ONE_TWO_THREE,
            min_bound=0,
            max_bound=0,
        )

        gen = sampler_router.generator_from_command(command1)
        assert next(gen) == ""

    @pytest.mark.parametrize(
        ("sampler_router", "expected"),
        [
            (
                lazy_fixture("random_sampler_router"),
                ["three", "three,one", "one", "two,three"],
            ),
            (
                lazy_fixture("cyclical_sampler_router"),
                ONE_TWO_THREE + ONE_TWO_THREEx2 + ONE_TWO_THREE,
            ),
            (
                lazy_fixture("combinatorial_sampler_router"),
                ONE_TWO_THREE + ONE_TWO_THREEx2,
            ),
        ],
    )
    def test_variant_with_bound(
        self,
        sampler_router: ConcreteSamplerRouter,
        expected: list[str],
    ):
        sampler = sampler_router._samplers[SamplingMethod.DEFAULT]

        variant_values = ONE_TWO_THREE
        command1 = VariantCommand.from_literals_and_weights(
            variant_values,
            min_bound=1,
            max_bound=2,
        )
        gen = sampler_router.generator_from_command(command1)

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
        ("sampler_router", "expected"),
        [
            (
                lazy_fixture("random_sampler_router"),
                ["three", "three and one", "one", "two and three"],
            ),
            (
                lazy_fixture("cyclical_sampler_router"),
                ONE_TWO_THREE + ONE_TWO_THREEx2and + ONE_TWO_THREE,
            ),
            (
                lazy_fixture("combinatorial_sampler_router"),
                ONE_TWO_THREE + ONE_TWO_THREEx2and,
            ),
        ],
    )
    def test_variant_with_bound_and_sep(
        self,
        sampler_router: ConcreteSamplerRouter,
        expected: list[str],
    ):
        sampler = sampler_router._samplers[SamplingMethod.DEFAULT]

        command1 = VariantCommand.from_literals_and_weights(
            ONE_TWO_THREE,
            min_bound=1,
            max_bound=2,
            separator=" and ",
        )

        gen = sampler_router.generator_from_command(command1)

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

    @pytest.mark.parametrize(
        ("sampler_router", "expected"),
        [
            (lazy_fixture("random_sampler_router"), ["red triangle", "blue circle"]),
            (
                lazy_fixture("cyclical_sampler_router"),
                zipstr(RED_GREEN_BLUE, SHAPES, sep=" "),
            ),
            (
                lazy_fixture("combinatorial_sampler_router"),
                cross(RED_GREEN_BLUE, SHAPES, sep=" "),
            ),
        ],
    )
    def test_two_variants(
        self,
        sampler_router: ConcreteSamplerRouter,
        expected: list[str],
    ):
        sampler = sampler_router._samplers[SamplingMethod.DEFAULT]

        command1 = VariantCommand.from_literals_and_weights(RED_GREEN_BLUE)
        command2 = LiteralCommand(" ")
        command3 = VariantCommand.from_literals_and_weights(SHAPES)

        sequence = SequenceCommand([command1, command2, command3])

        gen = sampler_router.generator_from_command(sequence)

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
        ("sampler_router", "expected"),
        [
            (lazy_fixture("random_sampler_router"), ["red triangle", "blue circle"]),
            (
                lazy_fixture("cyclical_sampler_router"),
                zipstr(RED_AND_GREEN, SHAPES, sep=" "),
            ),
            (
                lazy_fixture("combinatorial_sampler_router"),
                cross(RED_AND_GREEN, SHAPES, sep=" "),
            ),
        ],
    )
    def test_varied_prompt(
        self,
        sampler_router: ConcreteSamplerRouter,
        expected: list[str],
    ):
        sampler = sampler_router._samplers[SamplingMethod.DEFAULT]

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

        gen = sampler_router.generator_from_command(sequence)

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
        ("sampler_router", "key"),
        [
            (lazy_fixture("random_sampler_router"), "shuffled_colours"),
            (lazy_fixture("cyclical_sampler_router"), "wildcard_coloursx2"),
            (lazy_fixture("combinatorial_sampler_router"), "wildcard_colours"),
        ],
    )
    def test_basic_wildcard(
        self,
        sampler_router: ConcreteSamplerRouter,
        key: str,
        data_lookups: dict[str, list[str]],
    ):
        command = WildcardCommand("colors*")

        gen = sampler_router.generator_from_command(command)

        with patch_random_sampler_wildcard_choice(data_lookups[key]):
            prompts = [next(gen) for _ in range(len(data_lookups[key]))]

        for prompt, e in zip(prompts, data_lookups[key]):
            assert prompt == e

    @pytest.mark.parametrize(
        ("sampler_router", "key"),
        [
            (lazy_fixture("random_sampler_router"), "shuffled_colours"),
            (lazy_fixture("cyclical_sampler_router"), "wildcard_coloursx2"),
            (lazy_fixture("combinatorial_sampler_router"), "wildcard_colours"),
        ],
    )
    def test_wildcard_with_literal(
        self,
        sampler_router: ConcreteSamplerRouter,
        key: str,
        data_lookups: dict[str, list[str]],
    ):
        sampler = sampler_router._samplers[SamplingMethod.DEFAULT]

        command = WildcardCommand("colors*")
        sequence = SequenceCommand.from_literals(
            [command, " ", "are", " ", LiteralCommand("cool")],
        )

        gen = sampler.generator_from_command(sequence)

        with patch_random_sampler_wildcard_choice(data_lookups[key]):
            prompts = [next(gen) for _ in range(len(data_lookups[key]))]

        for prompt, e in zip(prompts, data_lookups[key]):
            assert prompt == f"{e} are cool"

    @pytest.mark.parametrize(
        ("sampler_router", "key"),
        [
            (lazy_fixture("random_sampler_router"), "shuffled_colours"),
            (lazy_fixture("cyclical_sampler_router"), "wildcard_colours"),
            (lazy_fixture("combinatorial_sampler_router"), "wildcard_colours"),
        ],
    )
    def test_wildcard_with_variant(
        self,
        sampler_router: ConcreteSamplerRouter,
        key: str,
        data_lookups: dict[str, list[str]],
    ):
        sampler = sampler_router._samplers[SamplingMethod.DEFAULT]

        command1 = WildcardCommand("colors*")
        command3 = VariantCommand.from_literals_and_weights(SHAPES)
        sequence = SequenceCommand.from_literals([command1, " ", command3])

        gen = sampler.generator_from_command(sequence)

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
        ("sampler_router", "expected"),
        [
            # (lazy_fixture("random_sampler_router"), ""),
            (
                lazy_fixture("cyclical_sampler_router"),
                ["red", "green", "blue", "pink", "green", "blue"],
            ),
            (
                lazy_fixture("combinatorial_sampler_router"),
                ["red", "pink", "green", "blue"],
            ),
        ],
    )
    def test_variant_nested_in_wildcard(
        self,
        sampler_router: ConcreteSamplerRouter,
        expected: list[str],
    ):
        with patch.object(
            sampler_router._wildcard_manager,
            "get_all_values",
            return_value=["{red|pink}", "green", "blue"],
        ):
            wildcard_command = WildcardCommand("colours")
            sequence = SequenceCommand([wildcard_command])

            gen = sampler_router.generator_from_command(sequence)

            prompts = [next(gen) for _ in range(len(expected))]

            assert prompts == expected

    @pytest.mark.parametrize(
        ("sampler_router", "expected"),
        [
            (lazy_fixture("random_sampler_router"), []),  # TODO fix this
            (
                lazy_fixture("cyclical_sampler_router"),
                [
                    "red",
                    "green",
                    "blue",
                    "pink",
                    "green",
                    "blue",
                    "yellow",
                    "green",
                    "blue",
                ],
            ),
            (
                lazy_fixture("combinatorial_sampler_router"),
                ["red", "pink", "yellow", "green", "blue"],
            ),
        ],
    )
    def test_wildcard_nested_in_wildcard(
        self,
        sampler_router: ConcreteSamplerRouter,
        expected: list[str],
    ):
        test_colours = [
            ["__other_colours__", "green", "blue"],
            ["red", "pink", "yellow"],
        ]

        with patch.object(
            sampler_router._wildcard_manager,
            "get_all_values",
            side_effect=test_colours,
        ):
            wildcard_command = WildcardCommand("colours")
            sequence = SequenceCommand([wildcard_command])

            gen = sampler_router.generator_from_command(sequence)

            prompts = [next(gen) for _ in range(len(expected))]
            assert prompts == expected
