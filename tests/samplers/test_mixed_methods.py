from __future__ import annotations

import pytest
from dynamicprompts.commands import (
    Command,
    SamplingMethod,
    VariantCommand,
)
from dynamicprompts.sampling_context import SamplingContext

from tests.samplers.utils import (
    patch_random_sampler_variant_choices_with_literals,
    patch_random_sampler_wildcard_choice,
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
        combinatorial_sampling_context: SamplingContext,
        template: str,
        choices_side_effect: list[str | Command],
        expected: list[str],
    ):
        with patch_random_sampler_variant_choices_with_literals(choices_side_effect):
            prompts = list(combinatorial_sampling_context.sample_prompts(template, 3))
        assert [str(p) for p in prompts] == expected

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
        combinatorial_sampling_context: SamplingContext,
        template: str,
        choices_side_effect: list[str | Command] | None,
        expected: list[str],
    ):
        with patch_random_sampler_variant_choices_with_literals(choices_side_effect):
            prompts = list(combinatorial_sampling_context.sample_prompts(template, 3))
        assert [str(p) for p in prompts] == expected

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
        combinatorial_sampling_context: SamplingContext,
        template: str,
        choices_side_effect: list[str | Command],
        expected: list[str],
    ):
        with patch_random_sampler_variant_choices_with_literals(choices_side_effect):
            prompts = list(combinatorial_sampling_context.sample_prompts(template, 3))
        assert [str(p) for p in prompts] == expected

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
        combinatorial_sampling_context: SamplingContext,
        template: str,
        choices_side_effect: list[str | Command],
        expected: list[str],
    ):
        with patch_random_sampler_variant_choices_with_literals(choices_side_effect):
            prompts = list(combinatorial_sampling_context.sample_prompts(template, 3))
        assert [str(p) for p in prompts] == expected

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
        combinatorial_sampling_context: SamplingContext,
        template: str,
        choices_side_effect: list[str | Command],
        expected: list[str],
    ):
        with patch_random_sampler_variant_choices_with_literals(choices_side_effect):
            prompts = list(combinatorial_sampling_context.sample_prompts(template, 10))
        assert [str(p) for p in prompts] == expected

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
        combinatorial_sampling_context: SamplingContext,
        sampling_method: SamplingMethod,
        template: str,
        expected: list[str],
    ):
        carbike_variant = VariantCommand.from_literals_and_weights(
            ["car", "bike"],
            sampling_method=sampling_method,
        )
        prompts = combinatorial_sampling_context.sample_prompts(template, 8)
        with patch_random_sampler_variant_choices_with_literals(
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
        ):
            prompts = list(prompts)

        assert [str(p) for p in prompts] == expected

    @pytest.mark.parametrize(
        ("template", "choice_value", "expected"),
        [
            ("test __@colors-cold__", None, ["test blue"]),
            ("test __~colors-cold__", "green", ["test green"]),
        ],
    )
    def test_non_finite_wildcards(
        self,
        combinatorial_sampling_context: SamplingContext,
        template: str,
        choice_value: str,
        expected: list[str],
    ):
        prompts = combinatorial_sampling_context.sample_prompts(template, 3)
        if choice_value:
            with patch_random_sampler_wildcard_choice([choice_value] * 3):
                prompts = list(prompts)

        assert [str(p) for p in prompts] == expected

    @pytest.mark.parametrize(
        ("template", "choice_side_effect", "expected"),
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
        combinatorial_sampling_context: SamplingContext,
        template: str,
        choice_side_effect: list[str],
        expected: list[str],
    ):
        prompts = combinatorial_sampling_context.sample_prompts(template, 3)

        if choice_side_effect:
            with patch_random_sampler_wildcard_choice(choice_side_effect):
                prompts = list(prompts)

        assert [str(p) for p in prompts] == expected


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
        random_sampling_context: SamplingContext,
        template: str,
        choices_side_effect: list[str | Command],
        expected: list[str],
    ):
        with patch_random_sampler_variant_choices_with_literals(choices_side_effect):
            prompts = list(random_sampling_context.sample_prompts(template, 3))
        assert [str(p) for p in prompts] == expected


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
        cyclical_sampling_context: SamplingContext,
        template: str,
        choices_side_effect: list[str | Command],
        expected: list[str],
    ):
        with patch_random_sampler_variant_choices_with_literals(choices_side_effect):
            prompts = list(cyclical_sampling_context.sample_prompts(template, 3))
        assert [str(p) for p in prompts] == expected
