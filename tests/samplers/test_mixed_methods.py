from typing import Any
from unittest import mock

import pytest
from dynamicprompts.commands import (
    Command,
    LiteralCommand,
    SamplingMethod,
    SequenceCommand,
    VariantCommand,
)
from dynamicprompts.sampler_routers.concrete_sampler_router import (
    DEFAULT_RANDOM,
    ConcreteSamplerRouter,
)


def mock_choices_side_effect(literals: list[str | Command] | None) -> Any:
    if literals is None:
        raise ValueError("literals cannot be None")

    literal_lists = [
        [literal] for literal in SequenceCommand.from_literals(literals).tokens
    ]

    return mock.patch.object(DEFAULT_RANDOM, "choices", side_effect=[*literal_lists])


def mock_choice_side_effect(literals: list[str | Command] | None) -> Any:
    if literals is None:
        raise ValueError("literals cannot be None")

    literal_lists = list(SequenceCommand.from_literals(literals).tokens)

    return mock.patch.object(DEFAULT_RANDOM, "choice", side_effect=[*literal_lists])


def mock_return_value(val: str):
    return mock.patch.object(
        DEFAULT_RANDOM,
        "choice",
        return_value=LiteralCommand(val),
    )


class TestCombinatorialParent:
    @pytest.mark.parametrize(
        ("template", "choices_side_effect", "expected"),
        [
            ("A {@red|green} ball", None, ["A red ball"]),
            (
                "A {~red|green} ball",
                ["green", "green"],
                ["A green ball"],
            ),
        ],
    )
    def test_non_finite_variants(
        self,
        combinatorial_sampler_router: ConcreteSamplerRouter,
        template: str,
        choices_side_effect: list[str | Command],
        expected: list[str],
    ):

        prompts = combinatorial_sampler_router.sample_prompts(template, 3)
        if choices_side_effect:
            with mock_choices_side_effect(choices_side_effect):
                prompts = list(prompts)

        assert list(prompts) == expected

    @pytest.mark.parametrize(
        ("template", "choices_side_effect", "expected"),
        [
            (
                "A {red|green} {@ball|car}",
                None,
                ["A red ball", "A green car"],
            ),
            (
                "A {red|green} {~ball|car}",
                ["car", "car", "car"],
                ["A red car", "A green car"],
            ),
        ],
    )
    def test_mixed_non_finite_variants_last_position(
        self,
        combinatorial_sampler_router: ConcreteSamplerRouter,
        template: str,
        choices_side_effect: list[str | Command] | None,
        expected: list[str],
    ):
        prompts = combinatorial_sampler_router.sample_prompts(template, 3)

        if choices_side_effect:
            with mock_choices_side_effect(choices_side_effect):
                prompts = list(prompts)

        assert list(prompts) == expected

    @pytest.mark.parametrize(
        ("template", "choices_side_effect", "expected"),
        [
            (
                "A {@red|green} {ball|car}",
                None,
                ["A red ball", "A green car"],
            ),
            (
                "A {~red|green} {ball|car}",
                ["green", "green", "green"],
                ["A green ball", "A green car"],
            ),
        ],
    )
    def test_mixed_non_finite_variants_first_position(
        self,
        combinatorial_sampler_router: ConcreteSamplerRouter,
        template: str,
        choices_side_effect: list[str | Command],
        expected: list[str],
    ):
        prompts = combinatorial_sampler_router.sample_prompts(template, 3)

        if choices_side_effect:
            with mock_choices_side_effect(choices_side_effect):
                prompts = list(prompts)

        assert list(prompts) == expected

    @pytest.mark.parametrize(
        ("template", "choices_side_effect", "expected"),
        [
            (
                "A {@red|green} {ball|car} {at night|in the morning}",
                None,
                [
                    "A red ball at night",
                    "A green ball in the morning",
                    "A red car at night",
                ],
            ),
            (
                "A {~red|green} {ball|car} {at night|in the morning}",
                ["green", "green", "green", "green"],
                [
                    "A green ball at night",
                    "A green ball in the morning",
                    "A green car at night",
                ],
            ),
        ],
    )
    def test_mixed_non_finite_variants_multiple_variants(
        self,
        combinatorial_sampler_router: ConcreteSamplerRouter,
        template: str,
        choices_side_effect: list[str | Command],
        expected: list[str],
    ):
        prompts = combinatorial_sampler_router.sample_prompts(template, 3)

        if choices_side_effect:
            with mock_choices_side_effect(choices_side_effect):
                prompts = list(prompts)

        assert list(prompts) == expected

    @pytest.mark.parametrize(
        ("template", "choices_side_effect", "expected"),
        [
            (
                "A {red|{@green|blue}} {@ball|car}",
                None,
                ["A red ball", "A green car"],
            ),
            (
                "A {red|{~green|blue}} {~ball|car}",
                ["ball", "car", "blue", "ball"],
                ["A red ball", "A blue car"],
            ),
        ],
    )
    def test_nested_cyclical_variants(
        self,
        combinatorial_sampler_router: ConcreteSamplerRouter,
        template: str,
        choices_side_effect: list[str | Command],
        expected: list[str],
    ):
        prompts = combinatorial_sampler_router.sample_prompts(template, 10)

        if choices_side_effect:
            with mock_choices_side_effect(choices_side_effect):
                prompts = list(prompts)

        assert list(prompts) == expected

    @pytest.mark.parametrize(
        ("sampling_method", "template", "expected"),
        [
            (
                SamplingMethod.CYCLICAL,
                "A {red|blue|green|yellow|purple|black|white} {@ball|{!car|bike}}",
                [
                    "A red ball",
                    "A blue car",
                    "A green ball",
                    "A yellow bike",
                    "A purple ball",
                    "A black car",
                    "A white ball",
                ],
            ),
            (
                SamplingMethod.RANDOM,
                "A {red|blue|green|yellow|purple|black|white} {~ball|{!car|bike}}",
                [
                    "A red ball",
                    "A blue car",
                    "A green ball",
                    "A yellow bike",
                    "A purple ball",
                    "A black car",
                    "A white ball",
                ],
            ),
        ],
    )
    def test_combinatorial_nested_in_non_finite(
        self,
        combinatorial_sampler_router: ConcreteSamplerRouter,
        sampling_method: SamplingMethod,
        template: str,
        expected: list[str],
    ):

        carbike_variant = VariantCommand.from_literals_and_weights(
            ["car", "bike"],
            sampling_method=SamplingMethod.RANDOM,
        )
        prompts = combinatorial_sampler_router.sample_prompts(template, 8)
        if sampling_method == SamplingMethod.RANDOM:
            literals = [
                [literal]
                for literal in SequenceCommand.from_literals(
                    [
                        "ball",  # A red ball
                        carbike_variant,  # A blue car
                        "car",  # A blue car
                        "ball",  # A green ball
                        carbike_variant,
                        "bike",  # A yellow bike
                        "ball",  # A purple ball
                        carbike_variant,  # A black car
                        "car",  # A black car
                        "ball",  # A white ball
                        "ball",  # Extra - unused
                    ],
                ).tokens
            ]

            with mock.patch.object(DEFAULT_RANDOM, "choices", side_effect=[*literals]):
                prompts = list(prompts)

        assert list(prompts) == expected

    @pytest.mark.parametrize(
        ("template", "choice_value", "expected"),
        [
            ("test __@colors-cold__", None, ["test blue"]),
            ("test __~colors-cold__", "green", ["test green"]),
        ],
    )
    def test_non_finite_wildcards(
        self,
        combinatorial_sampler_router: ConcreteSamplerRouter,
        template: str,
        choice_value: str,
        expected: list[str],
    ):

        prompts = combinatorial_sampler_router.sample_prompts(template, 3)
        if choice_value:
            with mock_return_value(choice_value):
                prompts = list(prompts)

        assert list(prompts) == expected

    @pytest.mark.parametrize(
        ("template", "choices_side_effect", "expected"),
        [
            (
                "{test1|test2} __@colors-cold__",
                None,
                ["test1 blue", "test2 green"],
            ),
            (
                "{test1|test2} __~colors-cold__",
                ["green", "green", "green", "green", "green", "green"],
                ["test1 green", "test2 green"],
            ),
        ],
    )
    def test_mixed_non_finite_wildcards_last_position(
        self,
        combinatorial_sampler_router: ConcreteSamplerRouter,
        template: str,
        choices_side_effect: list[str | Command],
        expected: list[str],
    ):
        prompts = combinatorial_sampler_router.sample_prompts(template, 3)

        if choices_side_effect:
            with mock_choice_side_effect(choices_side_effect):
                prompts = list(prompts)

        assert list(prompts) == expected


class TestRandomParent:
    @pytest.mark.parametrize(
        ("template", "choices_side_effect", "expected"),
        [
            ("A {@red|green} ball", None, ["A red ball", "A green ball", "A red ball"]),
            (
                "A {!red|green} ball",
                ["red", "green", "red"],
                ["A red ball", "A green ball", "A red ball"],
            ),
        ],
    )
    def test_variants(
        self,
        random_sampler_router: ConcreteSamplerRouter,
        template: str,
        choices_side_effect: list[str | Command],
        expected: list[str],
    ):

        prompts = random_sampler_router.sample_prompts(template, 3)
        if choices_side_effect:
            with mock_choices_side_effect(choices_side_effect):
                prompts = list(prompts)
        assert list(prompts) == expected


class TestCyclicalParent:
    @pytest.mark.parametrize(
        ("template", "choices_side_effect", "expected"),
        [
            ("A {!red|green} ball", None, ["A red ball", "A green ball", "A red ball"]),
            (
                "A {~red|green} ball",
                ["red", "green", "red"],
                ["A red ball", "A green ball", "A red ball"],
            ),
        ],
    )
    def test_variants(
        self,
        cyclical_sampler_router: ConcreteSamplerRouter,
        template: str,
        choices_side_effect: list[str | Command],
        expected: list[str],
    ):

        prompts = cyclical_sampler_router.sample_prompts(template, 3)
        if choices_side_effect:
            with mock_choices_side_effect(choices_side_effect):
                prompts = list(prompts)
        assert list(prompts) == expected
