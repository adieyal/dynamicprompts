import random
from itertools import cycle, islice, zip_longest
from unittest import mock

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

from tests.consts import ONE_TWO_THREE, RED_AND_GREEN, RED_GREEN_BLUE, SHAPES
from tests.utils import cross, zipstr

ONE_TWO_THREEx2 = cross(ONE_TWO_THREE, ONE_TWO_THREE)
ONE_TWO_THREEx2and = cross(ONE_TWO_THREE, ONE_TWO_THREE, sep=" and ")


def get_router(sampler_router: str, request: FixtureRequest) -> ConcreteSamplerRouter:
    return request.getfixturevalue(sampler_router)


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
            ("random_sampler_router", "one two three"),
            ("cyclical_sampler_router", "one two three"),
            ("combinatorial_sampler_router", "one two three"),
        ],
    )
    def test_prompts(
        self,
        sampler_router: str,
        expected: str,
        request: FixtureRequest,
    ):
        router = get_router(sampler_router, request)
        sequence = SequenceCommand.from_literals(["one", " ", "two", " ", "three"])
        prompt = next(router.generator_from_command(sequence))
        assert prompt == expected

    @pytest.mark.parametrize(
        ("sampler_router", "expected"),
        [
            ("random_sampler_router", "A|sentence"),
            ("cyclical_sampler_router", "A|sentence"),
            ("combinatorial_sampler_router", "A|sentence"),
        ],
    )
    def test_custom_separator(
        self,
        sampler_router: str,
        expected: str,
        request: FixtureRequest,
    ):
        router = get_router(sampler_router, request)

        command1 = LiteralCommand("A")
        command2 = LiteralCommand("sentence")
        sequence = SequenceCommand([command1, command2], separator="|")
        prompt = next(router.generator_from_command(sequence))
        assert prompt == expected


class TestLiteralCommand:
    @pytest.mark.parametrize(
        ("sampler_router", "expected"),
        [
            ("random_sampler_router", "one"),
            ("cyclical_sampler_router", "one"),
            ("combinatorial_sampler_router", "one"),
        ],
    )
    def test_single_literal(
        self,
        sampler_router: str,
        expected: str,
        request: FixtureRequest,
    ):
        router = get_router(sampler_router, request)

        literal = LiteralCommand("one")
        gen = router.generator_from_command(literal)
        assert next(gen) == expected

    @pytest.mark.parametrize(
        ("sampler_router", "expected"),
        [
            ("random_sampler_router", "one two three"),
            ("cyclical_sampler_router", "one two three"),
            ("combinatorial_sampler_router", "one two three"),
        ],
    )
    def test_multiple_literals(
        self,
        sampler_router: str,
        expected: str,
        request: FixtureRequest,
    ):
        router = get_router(sampler_router, request)

        sequence = SequenceCommand.from_literals(["one", " ", "two", " ", "three"])
        prompts = router.generator_from_command(sequence)

        assert next(prompts) == expected


class TestVariantCommand:
    @pytest.mark.parametrize(
        ("sampler_router"),
        [
            ("random_sampler_router"),
            ("cyclical_sampler_router"),
            ("combinatorial_sampler_router"),
        ],
    )
    def test_empty_variant(self, sampler_router: str, request: FixtureRequest):
        router = get_router(sampler_router, request)

        command = VariantCommand([])
        prompts = router.generator_from_command(command)
        assert len(list(prompts)) == 0

    @pytest.mark.parametrize(
        ("sampler_router", "expected"),
        [
            ("random_sampler_router", "one"),
            ("cyclical_sampler_router", "one"),
            ("combinatorial_sampler_router", "one"),
        ],
    )
    def test_single_variant(
        self,
        sampler_router: str,
        expected: str,
        request: FixtureRequest,
    ):
        router = get_router(sampler_router, request)

        command = VariantCommand.from_literals_and_weights(["one"])

        gen = router.generator_from_command(command)
        assert next(gen) == expected

    @pytest.mark.parametrize(
        ("sampler_router", "expected"),
        [
            ("random_sampler_router", ["one", "three", "two", "one"]),
            ("cyclical_sampler_router", ["one", "two", "three", "one", "two"]),
            ("combinatorial_sampler_router", ["one", "two", "three"]),
        ],
    )
    def test_multiple_variant(
        self,
        sampler_router: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        router = get_router(sampler_router, request)

        command = VariantCommand.from_literals_and_weights(ONE_TWO_THREE)
        sampler = router._samplers[SamplingMethod.DEFAULT]

        gen = sampler.generator_from_command(command)

        if isinstance(sampler, RandomSampler):
            with mock.patch.object(sampler, "_get_choices") as get_choices:
                random_choices = [[LiteralCommand(e)] for e in expected]

                get_choices.side_effect = random_choices
                prompts = [next(gen) for _ in expected]
        else:
            prompts = [next(gen) for _ in expected]

        for prompt, e in zip(prompts, expected):
            assert prompt == e

    @pytest.mark.parametrize(
        ("sampler_router", "expected"),
        [
            ("random_sampler_router", ["three", "three", "one", "two"]),
            ("cyclical_sampler_router", ["one", "two", "three", "one", "two"]),
            ("combinatorial_sampler_router", ["one", "two", "three"]),
        ],
    )
    def test_variant_with_literal(
        self,
        sampler_router: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        router = get_router(sampler_router, request)
        sampler = router._samplers[SamplingMethod.DEFAULT]

        command1 = VariantCommand.from_literals_and_weights(ONE_TWO_THREE)
        command2 = LiteralCommand(" circles")
        sequence = SequenceCommand([command1, command2])

        gen = router.generator_from_command(sequence)

        if isinstance(sampler, RandomSampler):
            with mock.patch.object(sampler, "_get_choices") as get_choices:
                random_choices = [[LiteralCommand(e)] for e in expected]

                get_choices.side_effect = random_choices
                prompts = [next(gen) for _ in expected]
        else:
            prompts = [next(gen) for _ in expected]

        for prompt, e in zip(prompts, expected):
            assert prompt == f"{e} circles"

    @pytest.mark.parametrize(
        ("sampler_router"),
        [
            ("random_sampler_router"),
            ("cyclical_sampler_router"),
            ("combinatorial_sampler_router"),
        ],
    )
    def test_variant_with_zero_bound(
        self,
        sampler_router: str,
        request: FixtureRequest,
    ):
        router = get_router(sampler_router, request)

        command1 = VariantCommand.from_literals_and_weights(
            ONE_TWO_THREE,
            min_bound=0,
            max_bound=0,
        )

        gen = router.generator_from_command(command1)
        assert next(gen) == ""

    @pytest.mark.parametrize(
        ("sampler_router", "expected"),
        [
            ("random_sampler_router", ["three", "three,one", "one", "two,three"]),
            (
                "cyclical_sampler_router",
                ONE_TWO_THREE + ONE_TWO_THREEx2 + ONE_TWO_THREE,
            ),
            ("combinatorial_sampler_router", ONE_TWO_THREE + ONE_TWO_THREEx2),
        ],
    )
    def test_variant_with_bound(
        self,
        sampler_router: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        router = get_router(sampler_router, request)
        sampler = router._samplers[SamplingMethod.DEFAULT]

        variant_values = ONE_TWO_THREE
        command1 = VariantCommand.from_literals_and_weights(
            variant_values,
            min_bound=1,
            max_bound=2,
        )
        gen = router.generator_from_command(command1)

        if isinstance(sampler, RandomSampler):
            with mock.patch.object(sampler, "_get_choices") as get_choices:
                random_choices = []
                for e in expected:
                    parts = e.split(",")
                    random_choices.append([LiteralCommand(p) for p in parts])

                get_choices.side_effect = random_choices
                prompts = [next(gen) for _ in expected]
        else:
            prompts = [next(gen) for _ in expected]

        for prompt, e in zip(prompts, expected):
            assert prompt == e

    @pytest.mark.parametrize(
        ("sampler_router", "expected"),
        [
            (
                "random_sampler_router",
                ["three", "three and one", "one", "two and three"],
            ),
            (
                "cyclical_sampler_router",
                ONE_TWO_THREE + ONE_TWO_THREEx2and + ONE_TWO_THREE,
            ),
            ("combinatorial_sampler_router", ONE_TWO_THREE + ONE_TWO_THREEx2and),
        ],
    )
    def test_variant_with_bound_and_sep(
        self,
        sampler_router: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        router = get_router(sampler_router, request)
        sampler = router._samplers[SamplingMethod.DEFAULT]

        command1 = VariantCommand.from_literals_and_weights(
            ONE_TWO_THREE,
            min_bound=1,
            max_bound=2,
            separator=" and ",
        )

        gen = router.generator_from_command(command1)

        if isinstance(sampler, RandomSampler):
            with mock.patch.object(sampler, "_get_choices") as get_choices:
                random_choices = []
                for e in expected:
                    parts = e.split(" and ")
                    random_choices.append([LiteralCommand(p) for p in parts])

                get_choices.side_effect = random_choices
                prompts = [next(gen) for _ in expected]
        else:
            prompts = [next(gen) for _ in expected]

        for prompt, e in zip(prompts, expected):
            assert prompt == e

    @pytest.mark.parametrize(
        ("sampler_router", "expected"),
        [
            ("random_sampler_router", ["red triangle", "blue circle"]),
            ("cyclical_sampler_router", zipstr(RED_GREEN_BLUE, SHAPES, sep=" ")),
            ("combinatorial_sampler_router", cross(RED_GREEN_BLUE, SHAPES, sep=" ")),
        ],
    )
    def test_two_variants(
        self,
        sampler_router: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        router = get_router(sampler_router, request)
        sampler = router._samplers[SamplingMethod.DEFAULT]

        command1 = VariantCommand.from_literals_and_weights(RED_GREEN_BLUE)
        command2 = LiteralCommand(" ")
        command3 = VariantCommand.from_literals_and_weights(SHAPES)

        sequence = SequenceCommand([command1, command2, command3])

        gen = router.generator_from_command(sequence)

        if isinstance(sampler, RandomSampler):
            with mock.patch.object(sampler, "_get_choices") as get_choices:
                random_choices = []
                for e in expected:
                    parts = e.split(" ")
                    random_choices += [[LiteralCommand(p)] for p in parts]

                get_choices.side_effect = random_choices
                prompts = [next(gen) for _ in expected]
        else:
            prompts = [next(gen) for _ in expected]

        for prompt, e in zip(prompts, expected):
            assert prompt == e

    @pytest.mark.parametrize(
        ("sampler_router", "expected"),
        [
            ("random_sampler_router", ["red triangle", "blue circle"]),
            ("cyclical_sampler_router", zipstr(RED_AND_GREEN, SHAPES, sep=" ")),
            ("combinatorial_sampler_router", cross(RED_AND_GREEN, SHAPES, sep=" ")),
        ],
    )
    def test_varied_prompt(
        self,
        sampler_router: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        router = get_router(sampler_router, request)
        sampler = router._samplers[SamplingMethod.DEFAULT]

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

        gen = router.generator_from_command(sequence)

        if isinstance(sampler, RandomSampler):
            with mock.patch.object(sampler, "_get_choices") as get_choices:
                random_choices = []
                for e in expected:
                    parts = e.split(" ")
                    random_choices += [[LiteralCommand(p)] for p in parts]

                get_choices.side_effect = random_choices
                prompts = [next(gen) for _ in expected]
        else:
            prompts = [next(gen) for _ in expected]

        for prompt, e in zip(prompts, expected):
            assert prompt == f"{e} are cool"


class TestWildcardsCommand:
    @pytest.mark.parametrize(
        ("sampler_router", "key"),
        [
            ("random_sampler_router", "shuffled_colours"),
            ("cyclical_sampler_router", "wildcard_coloursx2"),
            ("combinatorial_sampler_router", "wildcard_colours"),
        ],
    )
    def test_basic_wildcard(
        self,
        sampler_router: str,
        key: str,
        request: FixtureRequest,
        data_lookups: dict[str, list[str]],
    ):
        router = get_router(sampler_router, request)
        sampler = router._samplers[SamplingMethod.DEFAULT]

        command = WildcardCommand("colors*")

        gen = router.generator_from_command(command)

        if isinstance(sampler, RandomSampler):
            with mock.patch.object(sampler._random, "choice") as get_choices:
                shuffled_colours = data_lookups[key]

                random_choices = [LiteralCommand(c) for c in shuffled_colours]

                get_choices.side_effect = random_choices

                prompts = [next(gen) for _ in range(len(data_lookups[key]))]
        else:
            prompts = [next(gen) for _ in range(len(data_lookups[key]))]

        for prompt, e in zip(prompts, data_lookups[key]):
            assert prompt == e

    @pytest.mark.parametrize(
        ("sampler_router", "key"),
        [
            ("random_sampler_router", "shuffled_colours"),
            ("cyclical_sampler_router", "wildcard_coloursx2"),
            ("combinatorial_sampler_router", "wildcard_colours"),
        ],
    )
    def test_wildcard_with_literal(
        self,
        sampler_router: str,
        key: str,
        request: FixtureRequest,
        data_lookups: dict[str, list[str]],
    ):
        router = get_router(sampler_router, request)
        sampler = router._samplers[SamplingMethod.DEFAULT]

        command = WildcardCommand("colors*")
        sequence = SequenceCommand.from_literals(
            [command, " ", "are", " ", LiteralCommand("cool")],
        )

        gen = sampler.generator_from_command(sequence)

        if isinstance(sampler, RandomSampler):
            with mock.patch.object(sampler._random, "choice") as get_choices:
                shuffled_colours = data_lookups[key]

                random_choices = [LiteralCommand(c) for c in shuffled_colours]

                get_choices.side_effect = random_choices

                prompts = [next(gen) for _ in range(len(data_lookups[key]))]
        else:
            prompts = [next(gen) for _ in range(len(data_lookups[key]))]

        for prompt, e in zip(prompts, data_lookups[key]):
            assert prompt == f"{e} are cool"

    @pytest.mark.parametrize(
        ("sampler_router", "key"),
        [
            ("random_sampler_router", "shuffled_colours"),
            ("cyclical_sampler_router", "wildcard_colours"),
            ("combinatorial_sampler_router", "wildcard_colours"),
        ],
    )
    def test_wildcard_with_variant(
        self,
        sampler_router: str,
        key: str,
        request: FixtureRequest,
        data_lookups: dict[str, list[str]],
    ):
        router = get_router(sampler_router, request)
        sampler = router._samplers[SamplingMethod.DEFAULT]

        command1 = WildcardCommand("colors*")
        command3 = VariantCommand.from_literals_and_weights(SHAPES)
        sequence = SequenceCommand.from_literals([command1, " ", command3])

        gen = sampler.generator_from_command(sequence)

        if isinstance(sampler, RandomSampler):
            with mock.patch.object(sampler._random, "choice") as mock_choice:
                with mock.patch.object(sampler, "_get_choices") as mock_get_choice:
                    shuffled_colours = data_lookups[key]
                    shuffled_shapes = SHAPES.copy()
                    random.shuffle(shuffled_shapes)

                    random_choices = [LiteralCommand(c) for c in shuffled_colours]

                    mock_choice.side_effect = random_choices
                    mock_get_choice.side_effect = [
                        [LiteralCommand(shape)] for shape in shuffled_shapes
                    ]

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
            # ("random_sampler_router", ""),
            (
                "cyclical_sampler_router",
                ["red", "green", "blue", "pink", "green", "blue"],
            ),
            ("combinatorial_sampler_router", ["red", "pink", "green", "blue"]),
        ],
    )
    def test_variant_nested_in_wildcard(
        self,
        sampler_router: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        router = get_router(sampler_router, request)

        with mock.patch.object(
            router._wildcard_manager,
            "get_all_values",
            return_value=["{red|pink}", "green", "blue"],
        ):
            wildcard_command = WildcardCommand("colours")
            sequence = SequenceCommand([wildcard_command])

            gen = router.generator_from_command(sequence)

            prompts = [next(gen) for _ in range(len(expected))]

            assert prompts == expected

    @pytest.mark.parametrize(
        ("sampler_router", "expected"),
        [
            ("random_sampler_router", []),  # TODO fix this
            (
                "cyclical_sampler_router",
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
                "combinatorial_sampler_router",
                ["red", "pink", "yellow", "green", "blue"],
            ),
        ],
    )
    def test_wildcard_nested_in_wildcard(
        self,
        sampler_router: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        router = get_router(sampler_router, request)

        test_colours = [
            ["__other_colours__", "green", "blue"],
            ["red", "pink", "yellow"],
        ]

        with mock.patch.object(
            router._wildcard_manager,
            "get_all_values",
            side_effect=test_colours,
        ):
            wildcard_command = WildcardCommand("colours")
            sequence = SequenceCommand([wildcard_command])

            gen = router.generator_from_command(sequence)

            prompts = [next(gen) for _ in range(len(expected))]
            assert prompts == expected
