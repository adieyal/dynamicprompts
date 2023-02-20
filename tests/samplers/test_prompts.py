from __future__ import annotations

import random
from unittest import mock

import pytest
from dynamicprompts.commands import (
    LiteralCommand,
    SamplingMethod,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.sampler_routers.concrete_sampler_router import ConcreteSamplerRouter
from dynamicprompts.samplers import CombinatorialSampler, CyclicalSampler, RandomSampler
from dynamicprompts.samplers.base import SamplerRouter
from dynamicprompts.wildcardmanager import WildcardManager
from pytest import FixtureRequest

from tests.consts import RED_GREEN_BLUE
from tests.utils import cross, interleave, zipstr


@pytest.fixture
def data_lookups(wildcard_manager: WildcardManager) -> dict[str, list[str]]:
    wildcard_colours = wildcard_manager.get_all_values("colors*")
    shuffled_colours = wildcard_colours.copy()
    random.shuffle(shuffled_colours)

    return {
        "wildcard_colours": wildcard_colours,
        "shuffled_colours": shuffled_colours,
    }


class TestPrompts:
    @pytest.mark.parametrize(
        ("sampler_manager"),
        [
            ("random_sampler_router"),
            ("cyclical_sampler_router"),
            ("combinatorial_sampler_router"),
        ],
    )
    def test_empty(self, sampler_manager: str, request: FixtureRequest):
        manager: SamplerRouter = request.getfixturevalue(sampler_manager)

        prompts = list(manager.sample_prompts("", 5))
        assert prompts == []

    @pytest.mark.parametrize(
        ("sampler_manager", "expected"),
        [
            ("random_sampler_router", ["A literal sentence"] * 5),
            ("cyclical_sampler_router", ["A literal sentence"] * 5),
            ("combinatorial_sampler_router", ["A literal sentence"]),
        ],
    )
    def test_literals(
        self,
        sampler_manager: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        manager: SamplerRouter = request.getfixturevalue(sampler_manager)

        template = "A literal sentence"
        assert list(manager.sample_prompts(template, 5)) == expected

    @pytest.mark.parametrize(
        ("sampler_manager", "expected"),
        [
            ("random_sampler_router", ["Test [low emphasis]"] * 5),
            ("cyclical_sampler_router", ["Test [low emphasis]"] * 5),
            ("combinatorial_sampler_router", ["Test [low emphasis]"]),
        ],
    )
    def test_literal_with_square_brackets(
        self,
        sampler_manager: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        manager: SamplerRouter = request.getfixturevalue(sampler_manager)

        template = "Test [low emphasis]"
        assert list(manager.sample_prompts(template, 5)) == expected

    @pytest.mark.parametrize(
        ("sampler_manager", "expected"),
        [
            (
                "random_sampler_router",
                ["circle", "circle", "square", "circle", "square"],
            ),
            (
                "cyclical_sampler_router",
                ["square", "circle", "square", "circle", "square"],
            ),
            ("combinatorial_sampler_router", ["square", "circle"]),
        ],
    )
    def test_variants(
        self,
        sampler_manager: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        manager: ConcreteSamplerRouter = request.getfixturevalue(sampler_manager)
        sampler = manager._samplers[SamplingMethod.DEFAULT]

        template = "A red {square|circle}"

        if isinstance(sampler, RandomSampler):
            random_choices = [[LiteralCommand(v)] for v in expected]
            with mock.patch.object(
                sampler._random,
                "choices",
                side_effect=random_choices,
            ):
                prompts = list(manager.sample_prompts(template, 5))
        else:
            prompts = manager.sample_prompts(template, 5)

        for prompt, e in zip(prompts, expected):
            assert prompt == f"A red {e}"

    @pytest.mark.parametrize(
        ("sampler_manager", "expected"),
        [
            (
                "random_sampler_router",
                [
                    "red",
                    "red",
                    "red",
                    "red",
                    "blue",
                ],  # TODO not correctly handling blanks
            ),
            (
                "cyclical_sampler_router",
                ["red", "blue", "", "red", "blue"],
            ),
            ("combinatorial_sampler_router", ["red", "blue", ""]),
        ],
    )
    def test_variant_with_blank(
        self,
        sampler_manager: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        manager: ConcreteSamplerRouter = request.getfixturevalue(sampler_manager)
        sampler = manager._samplers[SamplingMethod.DEFAULT]

        template = "A {red|blue|} rose"

        if isinstance(sampler, RandomSampler):
            random_choices = [[LiteralCommand(v)] for v in expected]
            with mock.patch.object(
                sampler._random,
                "choices",
                side_effect=random_choices,
            ):
                prompts = list(manager.sample_prompts(template, 5))
        else:
            prompts = manager.sample_prompts(template, 5)

        expected_sentences = [f"A {e} rose" for e in expected]

        assert list(prompts) == expected_sentences

    @pytest.mark.parametrize(
        ("sampler_manager", "expected"),
        [
            (
                "random_sampler_router",
                [
                    "A red circle",
                    "A green square",
                    "A red square",
                    "A green square",
                    "A green square",
                ],
            ),
            (
                "cyclical_sampler_router",
                [
                    "A red square",
                    "A green circle",
                    "A red square",
                    "A green circle",
                    "A red square",
                ],
            ),
            (
                "combinatorial_sampler_router",
                ["A red square", "A red circle", "A green square", "A green circle"],
            ),
        ],
    )
    def test_two_variants(
        self,
        sampler_manager: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        manager: ConcreteSamplerRouter = request.getfixturevalue(sampler_manager)
        sampler = manager._samplers[SamplingMethod.DEFAULT]

        template = "A {red|green} {square|circle}"

        if isinstance(sampler, RandomSampler):
            split = [v.split() for v in expected]
            _, colours, shapes = zip(*split)
            random_choices = []

            for colour, shape in zip(colours, shapes):
                random_choices.append([LiteralCommand(colour)])
                random_choices.append([LiteralCommand(shape)])

            with mock.patch.object(
                sampler._random,
                "choices",
                side_effect=random_choices,
            ):
                prompts = list(manager.sample_prompts(template, 5))
        else:
            prompts = manager.sample_prompts(template, 5)

        assert list(prompts) == expected

    @pytest.mark.parametrize(
        ("sampler_manager", "expected"),
        [
            (
                "random_sampler_router",
                [
                    "A red,green square",
                    "A green,red circle",
                    "A red,green square",
                    "A red,green square",
                    "A red,green square",
                ],
            ),
            (
                "cyclical_sampler_router",
                [
                    "A red,green square",
                    "A green,red circle",
                    "A red,green square",
                    "A green,red circle",
                    "A red,green square",
                ],
            ),
            (
                "combinatorial_sampler_router",
                [
                    "A red,green square",
                    "A red,green circle",
                    "A green,red square",
                    "A green,red circle",
                ],
            ),
        ],
    )
    def test_combination_variants(
        self,
        sampler_manager: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        manager: ConcreteSamplerRouter = request.getfixturevalue(sampler_manager)
        sampler = manager._samplers[SamplingMethod.DEFAULT]

        template = "A {2$$red|green} {square|circle}"

        if isinstance(sampler, RandomSampler):
            split = [v.split() for v in expected]
            _, colours, shapes = zip(*split)
            colour_pairs = [c.split(",") for c in colours]

            random_choices = []

            for colour_pair, shape in zip(colour_pairs, shapes):
                random_choices.append([LiteralCommand(colour_pair[0])])
                random_choices.append([LiteralCommand(colour_pair[1])])

                random_choices.append([LiteralCommand(shape)])

            with mock.patch.object(
                sampler._random,
                "choices",
                side_effect=random_choices,
            ):
                prompts = list(manager.sample_prompts(template, 5))
        else:
            prompts = manager.sample_prompts(template, 5)

        assert list(prompts) == expected

    @pytest.mark.parametrize(
        ("sampler_manager", "expected"),
        [
            (
                "random_sampler_router",
                [
                    "A red,green square",
                    "A red square",
                    "A red,green square",
                    "A red,green square",
                    "A red,green square",
                ],
            ),
            (
                "cyclical_sampler_router",
                [
                    "A red square",
                    "A green square",
                    "A blue square",
                    "A red,green square",
                    "A red,blue square",
                ],
            ),
            (
                "combinatorial_sampler_router",
                [
                    "A red square",
                    "A green square",
                    "A blue square",
                    "A red,green square",
                    "A red,blue square",
                ],
            ),
        ],
    )
    def test_combination_variants_range(
        self,
        sampler_manager: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        manager: ConcreteSamplerRouter = request.getfixturevalue(sampler_manager)
        sampler = manager._samplers[SamplingMethod.DEFAULT]

        template = "A {1-2$$red|green|blue} square"

        if isinstance(sampler, RandomSampler):
            split = [v.split() for v in expected]
            _, colours, _ = zip(*split)
            colour_pairs = [c.split(",") for c in colours]
            random_choices = []

            for pair in colour_pairs:
                for p in pair:
                    random_choices.append([LiteralCommand(p)])

            with mock.patch.object(
                sampler._random,
                "choices",
                side_effect=random_choices,
            ):
                with mock.patch.object(
                    sampler._random,
                    "randint",
                    side_effect=[2, 1, 2, 2, 2],
                ):
                    prompts = list(manager.sample_prompts(template, 5))
        else:
            prompts = manager.sample_prompts(template, 5)

        assert list(prompts) == expected

    @pytest.mark.parametrize(
        ("sampler_manager", "expected"),
        [
            (
                "random_sampler_router",
                [
                    "red|blue",
                    "blue|green",
                ],
            ),
            (
                "cyclical_sampler_router",
                cross(RED_GREEN_BLUE, RED_GREEN_BLUE, sep="|"),
            ),
            (
                "combinatorial_sampler_router",
                cross(RED_GREEN_BLUE, RED_GREEN_BLUE, sep="|"),
            ),
        ],
    )
    def test_combination_variants_with_separator(
        self,
        sampler_manager: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        manager: ConcreteSamplerRouter = request.getfixturevalue(sampler_manager)
        sampler = manager._samplers[SamplingMethod.DEFAULT]

        template = "A {2$$|$$red|green|blue} square"

        if isinstance(sampler, RandomSampler):
            colour_pairs = [c.split("|") for c in expected]
            random_choices = []

            for pair in colour_pairs:
                for p in pair:
                    random_choices.append([LiteralCommand(p)])

            with mock.patch.object(
                sampler._random,
                "choices",
                side_effect=random_choices,
            ):
                with mock.patch.object(sampler._random, "randint", side_effect=[2, 2]):
                    prompts = list(manager.sample_prompts(template, len(expected)))

        else:
            prompts = manager.sample_prompts(template, len(expected))

        expected = [f"A {e} square" for e in expected]

        assert list(prompts) == expected

    @pytest.mark.parametrize(
        ("sampler_manager", "expected"),
        [
            # (  # TODO - fix this
            #     "random_sampler_router",
            #     [
            #         "blue", "red"
            #     ],
            # ),
            ("cyclical_sampler_router", RED_GREEN_BLUE),
            ("combinatorial_sampler_router", RED_GREEN_BLUE),
        ],
    )
    def test_weighted_variant(
        self,
        sampler_manager: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        manager: ConcreteSamplerRouter = request.getfixturevalue(sampler_manager)
        sampler = manager._samplers[SamplingMethod.DEFAULT]

        template = "A {1::red|2::green|3::blue} square"

        if isinstance(sampler, RandomSampler):
            random_choices = []

            for colour in expected:
                random_choices.append([LiteralCommand(colour)])

            with mock.patch.object(
                sampler._random,
                "choices",
                side_effect=random_choices,
            ):
                prompts = list(manager.sample_prompts(template, len(expected)))
        else:
            prompts = manager.sample_prompts(template, len(expected))

        expected = [f"A {e} square" for e in expected]

        assert list(prompts) == expected

    @pytest.mark.parametrize(
        ("sampler_manager", "expected"),
        [
            ("random_sampler_router", ["A green circle", "A red"]),
            (
                "cyclical_sampler_router",
                ["A red", "A green square", "A red", "A green circle"],
            ),
            (
                "combinatorial_sampler_router",
                ["A red", "A green square", "A green circle"],
            ),
        ],
    )
    def test_nested_variants(
        self,
        sampler_manager: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        manager: ConcreteSamplerRouter = request.getfixturevalue(sampler_manager)
        sampler = manager._samplers[SamplingMethod.DEFAULT]

        template = "A {red|green {square|circle}}"

        if isinstance(sampler, RandomSampler):
            variant = VariantCommand.from_literals_and_weights(
                ["square", "circle"],
                sampling_method=SamplingMethod.RANDOM,
            )
            random_choices = [
                [
                    SequenceCommand.from_literals(
                        [LiteralCommand("green "), variant],
                        sampling_method=SamplingMethod.RANDOM,
                    ),
                ],
                [LiteralCommand("circle", SamplingMethod.RANDOM)],
                [LiteralCommand("red", SamplingMethod.RANDOM)],
            ]

            with mock.patch.object(
                sampler._random,
                "choices",
                side_effect=random_choices,
            ):
                prompts = list(manager.sample_prompts(template, len(expected)))
        else:
            prompts = manager.sample_prompts(template, len(expected))

        assert list(prompts) == expected

    @pytest.mark.parametrize(
        ("sampler_manager", "expected"),
        [
            (
                "random_sampler_router",
                ["blue", "red"],
            ),
            ("cyclical_sampler_router", RED_GREEN_BLUE * 2),
            ("combinatorial_sampler_router", RED_GREEN_BLUE),
        ],
    )
    def test_wildcards(
        self,
        sampler_manager: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        manager: ConcreteSamplerRouter = request.getfixturevalue(sampler_manager)
        sampler = manager._samplers[SamplingMethod.DEFAULT]

        template = "A __colours__ square"

        with mock.patch.object(
            manager._wildcard_manager,
            "get_all_values",
            side_effect=[RED_GREEN_BLUE],
        ):

            if isinstance(sampler, RandomSampler):
                random_choices = []

                for colour in expected:
                    random_choices.append(LiteralCommand(colour))

                with mock.patch.object(
                    sampler._random,
                    "choice",
                    side_effect=random_choices,
                ):
                    prompts = list(manager.sample_prompts(template, len(expected)))

            else:
                prompts = manager.sample_prompts(template, len(expected))

            expected = [f"A {e} square" for e in expected]

            assert list(prompts) == expected

    @pytest.mark.parametrize(
        ("sampler_manager", "expected"),
        [
            ("random_sampler_router", ["A __missing__ wildcard"] * 5),
            ("cyclical_sampler_router", ["A __missing__ wildcard"] * 5),
            ("combinatorial_sampler_router", []),
        ],
    )
    def test_missing_wildcard(
        self,
        sampler_manager: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        manager: ConcreteSamplerRouter = request.getfixturevalue(sampler_manager)
        template = "A __missing__ wildcard"

        prompts = manager.sample_prompts(template, len(expected))

        assert list(prompts) == expected

    @pytest.mark.parametrize(
        ("sampler_manager", "key"),
        [
            ("random_sampler_router", "shuffled_colours"),
            ("cyclical_sampler_router", "wildcard_colours"),
            ("combinatorial_sampler_router", "wildcard_colours"),
        ],
    )
    def test_nested_wildcard(
        self,
        sampler_manager: str,
        key: str,
        request: FixtureRequest,
        data_lookups: dict[str, list[str]],
    ):
        manager: ConcreteSamplerRouter = request.getfixturevalue(sampler_manager)
        sampler = manager._samplers[SamplingMethod.DEFAULT]
        template = "{__colors*__}"

        expected = data_lookups[key]
        if isinstance(sampler, RandomSampler):
            random_choices = []

            for colour in expected:
                random_choices.append(LiteralCommand(colour))

            with mock.patch.object(
                sampler._random,
                "choice",
                side_effect=random_choices,
            ):
                prompts = list(manager.sample_prompts(template, len(expected)))
        else:
            prompts = manager.sample_prompts(template, len(expected))

        assert list(prompts) == expected

    @pytest.mark.parametrize(
        ("sampler_manager", "key"),
        [
            # ("random_sampler_router", "shuffled_colours"), # TODO - fix this
            ("cyclical_sampler_router", "wildcard_colours"),
            ("combinatorial_sampler_router", "wildcard_colours"),
        ],
    )
    def test_nested_wildcard_with_range_and_literal(
        self,
        sampler_manager: str,
        key: str,
        request: FixtureRequest,
        data_lookups: dict[str, list[str]],
    ):
        manager: ConcreteSamplerRouter = request.getfixturevalue(sampler_manager)
        sampler = manager._samplers[SamplingMethod.DEFAULT]

        template = "{2$$__colors*__|black}"
        expected = data_lookups[key]

        if isinstance(sampler, RandomSampler):
            random_choices = []
            variant_choices = [[LiteralCommand("black")], [WildcardCommand("colors*")]]

            for colour in expected:
                random_choices.append(LiteralCommand(colour))

            with mock.patch.object(
                sampler._random,
                "choice",
                side_effect=random_choices,
            ):
                with mock.patch.object(
                    sampler._random,
                    "choices",
                    side_effect=variant_choices,
                ):

                    black = ["black"] * len(expected)
                    arr1 = zipstr(expected, black, sep=",")
                    arr2 = zipstr(black, expected, sep=",")
                    expected = interleave(arr1, arr2)

                    prompts = list(manager.sample_prompts(template, len(expected)))
        else:
            if isinstance(sampler, CyclicalSampler):
                black = ["black"] * len(expected)
                arr1 = zipstr(expected, black, sep=",")
                arr2 = zipstr(black, expected, sep=",")
                expected = interleave(arr1, arr2)
            elif isinstance(sampler, CombinatorialSampler):
                expected = [f"{e},black" for e in expected] + [
                    f"black,{e}" for e in expected
                ]

            prompts = manager.sample_prompts(template, len(expected))

        assert list(prompts) == expected

    @pytest.mark.parametrize(
        ("sampler_manager"),
        [
            ("random_sampler_router"),
            ("cyclical_sampler_router"),
            ("combinatorial_sampler_router"),
        ],
    )
    def test_variants_with_larger_bounds_than_choices(
        self,
        sampler_manager: str,
        request: FixtureRequest,
    ):
        manager: ConcreteSamplerRouter = request.getfixturevalue(sampler_manager)

        template = "A red {3$$square|circle}"
        prompts = manager.sample_prompts(template, 10)

        for el in prompts:
            assert el in ["A red square,circle", "A red circle,square"]

    @pytest.mark.parametrize(
        ("sampler_manager"),
        [
            ("random_sampler_router"),
            ("cyclical_sampler_router"),
            ("combinatorial_sampler_router"),
        ],
    )
    def test_nospace_before_or_after_wildcard(
        self,
        sampler_manager: str,
        request: FixtureRequest,
    ):
        manager: ConcreteSamplerRouter = request.getfixturevalue(sampler_manager)
        template = "(__colors*__:2.3) "

        prompts = list(manager.sample_prompts(template, 20))

        for prompt in prompts:
            assert "( " not in prompt
            assert " :" not in prompt
