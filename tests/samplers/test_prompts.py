from __future__ import annotations

from itertools import tee
from unittest.mock import patch

import pytest
from dynamicprompts.commands import (
    LiteralCommand,
    SamplingMethod,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.samplers import (
    CombinatorialSampler,
    CyclicalSampler,
    RandomSampler,
)
from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.wildcards import WildcardManager
from dynamicprompts.wildcards.values import WildcardValues
from pytest_lazyfixture import lazy_fixture

from tests.conftest import sampling_context_lazy_fixtures
from tests.consts import RED_GREEN_BLUE
from tests.samplers.utils import (
    patch_random_sampler_variant_choices,
    patch_random_sampler_variant_choices_with_literals,
    patch_random_sampler_variant_num_choices,
    patch_random_sampler_wildcard_choice,
)
from tests.utils import cross, interleave, zipstr


@pytest.fixture
def data_lookups(wildcard_manager: WildcardManager) -> dict[str, WildcardValues]:
    wildcard_colours = wildcard_manager.get_values("colors*")
    shuffled_colours = wildcard_colours.shuffled()

    return {
        "wildcard_colours": wildcard_colours,
        "shuffled_colours": shuffled_colours,
    }


class TestPrompts:
    @pytest.mark.parametrize("sampling_context", sampling_context_lazy_fixtures)
    def test_empty(self, sampling_context: SamplingContext):
        prompts = list(sampling_context.sample_prompts("", 5))
        assert [str(p) for p in prompts] == []

    @pytest.mark.parametrize(
        ("sampling_context", "expected"),
        [
            (lazy_fixture("random_sampling_context"), ["A literal sentence"] * 5),
            (lazy_fixture("cyclical_sampling_context"), ["A literal sentence"] * 5),
            (lazy_fixture("combinatorial_sampling_context"), ["A literal sentence"]),
        ],
    )
    def test_literals(
        self,
        sampling_context: SamplingContext,
        expected: list[str],
    ):
        template = "A literal sentence"
        assert [
            str(p) for p in sampling_context.sample_prompts(template, 5)
        ] == expected

    @pytest.mark.parametrize(
        ("sampling_context", "expected"),
        [
            (lazy_fixture("random_sampling_context"), ["Test [low emphasis]"] * 5),
            (lazy_fixture("cyclical_sampling_context"), ["Test [low emphasis]"] * 5),
            (lazy_fixture("combinatorial_sampling_context"), ["Test [low emphasis]"]),
        ],
    )
    def test_literal_with_square_brackets(
        self,
        sampling_context: SamplingContext,
        expected: list[str],
    ):
        template = "Test [low emphasis]"
        assert [
            str(p) for p in sampling_context.sample_prompts(template, 5)
        ] == expected

    @pytest.mark.parametrize(
        ("sampling_context", "expected"),
        [
            (
                lazy_fixture("random_sampling_context"),
                ["circle", "circle", "square", "circle", "square"],
            ),
            (
                lazy_fixture("cyclical_sampling_context"),
                ["square", "circle", "square", "circle", "square"],
            ),
            (lazy_fixture("combinatorial_sampling_context"), ["square", "circle"]),
        ],
    )
    def test_variants(
        self,
        sampling_context: SamplingContext,
        expected: list[str],
    ):
        template = "A red {square|circle}"

        with patch_random_sampler_variant_choices_with_literals(expected):
            prompts = list(sampling_context.sample_prompts(template, 5))

        for prompt, e in zip(prompts, expected):
            assert str(prompt) == f"A red {e}"

    @pytest.mark.parametrize(
        ("sampling_context", "expected"),
        [
            (
                lazy_fixture("random_sampling_context"),
                [
                    "red",
                    "red",
                    "red",
                    "red",
                    "blue",
                ],  # TODO not correctly handling blanks
            ),
            (
                lazy_fixture("cyclical_sampling_context"),
                ["red", "blue", "", "red", "blue"],
            ),
            (lazy_fixture("combinatorial_sampling_context"), ["red", "blue", ""]),
        ],
    )
    def test_variant_with_blank(
        self,
        sampling_context: SamplingContext,
        expected: list[str],
    ):
        template = "A {red|blue|} rose"

        with patch_random_sampler_variant_choices_with_literals(expected):
            prompts = list(sampling_context.sample_prompts(template, 5))

        expected_sentences = [f"A {e} rose" for e in expected]

        assert [str(p) for p in prompts] == expected_sentences

    @pytest.mark.parametrize(
        ("sampling_context", "expected"),
        [
            (
                lazy_fixture("random_sampling_context"),
                [
                    "A red circle",
                    "A green square",
                    "A red square",
                    "A green square",
                    "A green square",
                ],
            ),
            (
                lazy_fixture("cyclical_sampling_context"),
                [
                    "A red square",
                    "A green circle",
                    "A red square",
                    "A green circle",
                    "A red square",
                ],
            ),
            (
                lazy_fixture("combinatorial_sampling_context"),
                ["A red square", "A red circle", "A green square", "A green circle"],
            ),
        ],
    )
    def test_two_variants(
        self,
        sampling_context: SamplingContext,
        expected: list[str],
    ):
        sampler = sampling_context.default_sampler

        template = "A {red|green} {square|circle}"

        if isinstance(sampler, RandomSampler):
            split = [v.split() for v in expected]
            _, colours, shapes = zip(*split)
            random_choices = []

            for colour, shape in zip(colours, shapes):
                random_choices.append([LiteralCommand(colour)])
                random_choices.append([LiteralCommand(shape)])

            with patch_random_sampler_variant_choices(random_choices):
                prompts = list(sampling_context.sample_prompts(template, 5))
        else:
            prompts = sampling_context.sample_prompts(template, 5)

        assert [str(p) for p in prompts] == expected

    @pytest.mark.parametrize(
        ("sampling_context", "expected"),
        [
            (
                lazy_fixture("random_sampling_context"),
                [
                    "A red,green square",
                    "A green,red circle",
                    "A red,green square",
                    "A red,green square",
                    "A red,green square",
                ],
            ),
            (
                lazy_fixture("cyclical_sampling_context"),
                [
                    "A red,green square",
                    "A green,red circle",
                    "A red,green square",
                    "A green,red circle",
                    "A red,green square",
                ],
            ),
            (
                lazy_fixture("combinatorial_sampling_context"),
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
        sampling_context: SamplingContext,
        expected: list[str],
    ):
        sampler = sampling_context.default_sampler

        template = "A {2$$red|green} {square|circle}"

        if isinstance(sampler, RandomSampler):
            split = [v.split() for v in expected]
            _, colours, shapes = zip(*split)
            colour_pairs = [c.split(",") for c in colours]

            random_choices = []

            for colour_pair, shape in zip(colour_pairs, shapes):
                random_choices.append(
                    [LiteralCommand(colour_pair[0]), LiteralCommand(colour_pair[1])],
                )
                random_choices.append([LiteralCommand(shape)])

            with patch_random_sampler_variant_choices(random_choices):
                prompts = list(sampling_context.sample_prompts(template, 5))
        else:
            prompts = sampling_context.sample_prompts(template, 5)

        assert [str(p) for p in prompts] == expected

    @pytest.mark.parametrize(
        ("sampling_context", "expected"),
        [
            (
                lazy_fixture("random_sampling_context"),
                [
                    "A red,green square",
                    "A red square",
                    "A red,green square",
                    "A red,green square",
                    "A red,green square",
                ],
            ),
            (
                lazy_fixture("cyclical_sampling_context"),
                [
                    "A red square",
                    "A green square",
                    "A blue square",
                    "A red,green square",
                    "A red,blue square",
                ],
            ),
            (
                lazy_fixture("combinatorial_sampling_context"),
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
        sampling_context: SamplingContext,
        expected: list[str],
    ):
        sampler = sampling_context.default_sampler

        template = "A {1-2$$red|green|blue} square"

        if isinstance(sampler, RandomSampler):
            split = [v.split() for v in expected]
            _, colours, _ = zip(*split)
            colour_pairs = [c.split(",") for c in colours]
            random_choices = [
                [LiteralCommand(p) for p in pair] for pair in colour_pairs
            ]

            with patch_random_sampler_variant_choices(random_choices):
                with patch_random_sampler_variant_num_choices([2, 1, 2, 2, 2]):
                    prompts = list(sampling_context.sample_prompts(template, 5))
        else:
            prompts = sampling_context.sample_prompts(template, 5)

        assert [str(p) for p in prompts] == expected

    @pytest.mark.parametrize(
        ("sampling_context", "expected"),
        [
            (
                lazy_fixture("random_sampling_context"),
                [
                    "red|blue",
                    "blue|green",
                ],
            ),
            (
                lazy_fixture("cyclical_sampling_context"),
                cross(RED_GREEN_BLUE, RED_GREEN_BLUE, sep="|"),
            ),
            (
                lazy_fixture("combinatorial_sampling_context"),
                cross(RED_GREEN_BLUE, RED_GREEN_BLUE, sep="|"),
            ),
        ],
    )
    def test_combination_variants_with_separator(
        self,
        sampling_context: SamplingContext,
        expected: list[str],
    ):
        sampler = sampling_context.default_sampler

        template = "A {2$$|$$red|green|blue} square"

        if isinstance(sampler, RandomSampler):
            colour_pairs = [c.split("|") for c in expected]
            random_choices = [
                [LiteralCommand(p) for p in pair] for pair in colour_pairs
            ]

            with patch_random_sampler_variant_choices(random_choices):
                with patch_random_sampler_variant_num_choices([2, 2]):
                    prompts = list(
                        sampling_context.sample_prompts(template, len(expected)),
                    )

        else:
            prompts = sampling_context.sample_prompts(template, len(expected))

        expected = [f"A {e} square" for e in expected]

        assert [str(p) for p in prompts] == expected

    @pytest.mark.parametrize(
        ("sampling_context", "expected"),
        [
            # (  # TODO - fix this
            #     lazy_fixture("random_sampling_context"),
            #     [
            #         "blue", "red"
            #     ],
            # ),
            (lazy_fixture("cyclical_sampling_context"), RED_GREEN_BLUE),
            (lazy_fixture("combinatorial_sampling_context"), RED_GREEN_BLUE),
        ],
    )
    def test_weighted_variant(
        self,
        sampling_context: SamplingContext,
        expected: list[str],
    ):
        template = "A {1::red|2::green|3::blue} square"

        with patch_random_sampler_variant_choices_with_literals(expected):
            prompts = list(sampling_context.sample_prompts(template, len(expected)))

        expected = [f"A {e} square" for e in expected]

        assert [str(p) for p in prompts] == expected

    @pytest.mark.parametrize(
        ("sampling_context", "expected"),
        [
            (lazy_fixture("random_sampling_context"), ["A green circle", "A red"]),
            (
                lazy_fixture("cyclical_sampling_context"),
                ["A red", "A green square", "A red", "A green circle"],
            ),
            (
                lazy_fixture("combinatorial_sampling_context"),
                ["A red", "A green square", "A green circle"],
            ),
        ],
    )
    def test_nested_variants(
        self,
        sampling_context: SamplingContext,
        expected: list[str],
    ):
        sampler = sampling_context.default_sampler

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

            with patch_random_sampler_variant_choices(random_choices):
                prompts = list(sampling_context.sample_prompts(template, len(expected)))
        else:
            prompts = sampling_context.sample_prompts(template, len(expected))

        assert [str(p) for p in prompts] == expected

    @pytest.mark.parametrize(
        ("sampling_context", "expected"),
        [
            (
                lazy_fixture("random_sampling_context"),
                ["blue", "red"],
            ),
            (lazy_fixture("cyclical_sampling_context"), RED_GREEN_BLUE * 2),
            (lazy_fixture("combinatorial_sampling_context"), RED_GREEN_BLUE),
        ],
    )
    def test_wildcards(
        self,
        sampling_context: SamplingContext,
        expected: list[str],
    ):
        template = "A __colours__ square"

        with patch.object(
            sampling_context.wildcard_manager,
            "get_values",
            return_value=WildcardValues.from_items(RED_GREEN_BLUE),
        ):
            with patch_random_sampler_wildcard_choice(expected):
                prompts = list(sampling_context.sample_prompts(template, len(expected)))
            expected = [f"A {e} square" for e in expected]

            assert [str(p) for p in prompts] == expected

    @pytest.mark.parametrize(
        ("sampling_context", "expected"),
        [
            (lazy_fixture("random_sampling_context"), ["A __missing__ wildcard"] * 5),
            (lazy_fixture("cyclical_sampling_context"), ["A __missing__ wildcard"] * 5),
            (lazy_fixture("combinatorial_sampling_context"), []),
        ],
    )
    def test_missing_wildcard(
        self,
        sampling_context: SamplingContext,
        expected: list[str],
    ):
        wrap = sampling_context.wildcard_manager.wildcard_wrap
        prompts = sampling_context.sample_prompts(
            "A __missing__ wildcard".replace("__", wrap),
            len(expected),
        )

        assert [str(p) for p in prompts] == [ex.replace("__", wrap) for ex in expected]

    @pytest.mark.parametrize(
        ("sampling_context", "key"),
        [
            (lazy_fixture("random_sampling_context"), "shuffled_colours"),
            (lazy_fixture("cyclical_sampling_context"), "wildcard_colours"),
            (lazy_fixture("combinatorial_sampling_context"), "wildcard_colours"),
        ],
    )
    def test_nested_wildcard(
        self,
        sampling_context: SamplingContext,
        key: str,
        data_lookups: dict[str, list[str]],
    ):
        template = "{__colors*__}"

        expected = [[LiteralCommand(c)] for c in data_lookups[key]]
        with patch_random_sampler_variant_choices(expected):
            prompts = list(sampling_context.sample_prompts(template, len(expected)))

        assert [str(p) for p in prompts] == [v[0].literal for v in expected]

    @pytest.mark.parametrize(
        ("sampling_context", "key"),
        [
            # (lazy_fixture("random_sampling_context"), "shuffled_colours"), # TODO - fix this
            (lazy_fixture("cyclical_sampling_context"), "wildcard_colours"),
            (lazy_fixture("combinatorial_sampling_context"), "wildcard_colours"),
        ],
    )
    def test_nested_wildcard_with_range_and_literal(
        self,
        sampling_context: SamplingContext,
        key: str,
        data_lookups: dict[str, list[str]],
    ):
        sampler = sampling_context.default_sampler

        template = "{2$$__colors*__|black}"
        expected = data_lookups[key]

        if isinstance(sampler, RandomSampler):
            variant_choices = [[LiteralCommand("black")], [WildcardCommand("colors*")]]

            with patch_random_sampler_wildcard_choice(expected):
                with patch_random_sampler_variant_choices(variant_choices):
                    black = ["black"] * len(expected)
                    arr1 = zipstr(expected, black, sep=",")
                    arr2 = zipstr(black, expected, sep=",")
                    expected = interleave(arr1, arr2)

                    prompts = list(
                        sampling_context.sample_prompts(template, len(expected)),
                    )
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

            prompts = sampling_context.sample_prompts(template, len(expected))

        assert [str(p) for p in prompts] == expected

    @pytest.mark.parametrize(
        ("sampling_context", "key"),
        [
            # (lazy_fixture("random_sampling_context"), "shuffled_colours"), # TODO - fix this
            (lazy_fixture("cyclical_sampling_context"), "wildcard_colours"),
            (lazy_fixture("combinatorial_sampling_context"), "wildcard_colours"),
        ],
    )
    def test_nested_wildcard_with_range_min_without_max_and_literal(
            self,
            sampling_context: SamplingContext,
            key: str,
            data_lookups: dict[str, list[str]],
    ):
        sampler = sampling_context.default_sampler

        max_options = 3

        template = f"{{{max_options}-$$__colors*__}}"
        expected = data_lookups[key]

        if isinstance(sampler, RandomSampler):
            variant_choices = [[LiteralCommand("black")], [WildcardCommand("colors*")]]

            with patch_random_sampler_wildcard_choice(expected):
                with patch_random_sampler_variant_choices(variant_choices):
                    black = ["black"] * len(expected)
                    arr1 = zipstr(expected, black, sep=",")
                    arr2 = zipstr(black, expected, sep=",")
                    expected = interleave(arr1, arr2)

                    prompts = list(
                        sampling_context.sample_prompts(template, len(expected)),
                    )
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

            prompts = sampling_context.sample_prompts(template, len(expected))

        prompts, prompts_copy = tee(prompts)

        for el in prompts_copy:
            a = str(el).split(",")
            print(len(a), a)
            assert len(a) >= max_options

        # assert [str(p) for p in prompts] == expected

    @pytest.mark.parametrize(
        ("sampling_context"),
        [
            (lazy_fixture("random_sampling_context")),
            (lazy_fixture("cyclical_sampling_context")),
            (lazy_fixture("combinatorial_sampling_context")),
        ],
    )
    def test_variants_with_larger_bounds_than_choices(
        self,
        sampling_context: SamplingContext,
    ):
        template = "A red {3$$square|circle}"
        prompts = sampling_context.sample_prompts(template, 10)
        expected = ("A red square,circle", "A red circle,square")
        for el in prompts:
            assert str(el) in expected

    @pytest.mark.parametrize(
        ("sampling_context"),
        [
            (lazy_fixture("random_sampling_context")),
            (lazy_fixture("cyclical_sampling_context")),
            (lazy_fixture("combinatorial_sampling_context")),
        ],
    )
    def test_nospace_before_or_after_wildcard(
        self,
        sampling_context: SamplingContext,
    ):
        template = "(__colors*__:2.3) "

        prompts = [str(p) for p in sampling_context.sample_prompts(template, 20)]

        for prompt in prompts:
            assert "( " not in prompt
            assert " :" not in prompt
