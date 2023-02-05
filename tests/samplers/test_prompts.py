from unittest import mock

import pytest
from dynamicprompts.commands import (
    LiteralCommand,
    SamplingMethod,
)
from dynamicprompts.samplers import RandomSampler
from dynamicprompts.samplers.base import SamplerManager
from dynamicprompts.samplers.sampler_manager import ConcreteSamplerManager
from pytest import FixtureRequest


class TestPrompts:
    @pytest.mark.parametrize(
        ("sampler_manager"),
        [
            ("random_sampler_manager"),
            ("cyclical_sampler_manager"),
            ("combinatorial_sampler_manager"),
        ],
    )
    def test_empty(self, sampler_manager: str, request: FixtureRequest):
        manager: SamplerManager = request.getfixturevalue(sampler_manager)

        prompts = list(manager.sample_prompts("", 5))
        assert prompts == []

    @pytest.mark.parametrize(
        ("sampler_manager", "expected"),
        [
            ("random_sampler_manager", ["A literal sentence"] * 5),
            ("cyclical_sampler_manager", ["A literal sentence"] * 5),
            ("combinatorial_sampler_manager", ["A literal sentence"]),
        ],
    )
    def test_literals(
        self,
        sampler_manager: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        manager: SamplerManager = request.getfixturevalue(sampler_manager)

        template = "A literal sentence"
        assert list(manager.sample_prompts(template, 5)) == expected

    @pytest.mark.parametrize(
        ("sampler_manager", "expected"),
        [
            ("random_sampler_manager", ["Test [low emphasis]"] * 5),
            ("cyclical_sampler_manager", ["Test [low emphasis]"] * 5),
            ("combinatorial_sampler_manager", ["Test [low emphasis]"]),
        ],
    )
    def test_literal_with_square_brackets(
        self,
        sampler_manager: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        manager: SamplerManager = request.getfixturevalue(sampler_manager)

        template = "Test [low emphasis]"
        assert list(manager.sample_prompts(template, 5)) == expected

    @pytest.mark.parametrize(
        ("sampler_manager", "expected"),
        [
            (
                "random_sampler_manager",
                ["circle", "circle", "square", "circle", "square"],
            ),
            (
                "cyclical_sampler_manager",
                ["square", "circle", "square", "circle", "square"],
            ),
            ("combinatorial_sampler_manager", ["square", "circle"]),
        ],
    )
    def test_variants(
        self,
        sampler_manager: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        manager: ConcreteSamplerManager = request.getfixturevalue(sampler_manager)
        sampler = manager._samplers[SamplingMethod.DEFAULT]

        template = "A red {square|circle}"

        if isinstance(sampler, RandomSampler):
            sampler._random.choices = mock.Mock()
            sampler._random.choices.side_effect = [
                [LiteralCommand(v)] for v in expected
            ]
            prompts = manager.sample_prompts(template, 5)
        else:
            prompts = manager.sample_prompts(template, 5)

        for prompt, e in zip(prompts, expected):
            assert prompt == f"A red {e}"

    @pytest.mark.parametrize(
        ("sampler_manager", "expected"),
        [
            (
                "random_sampler_manager",
                [
                    "red",
                    "red",
                    "red",
                    "red",
                    "blue",
                ],  # TODO not correctly handling blanks
            ),
            (
                "cyclical_sampler_manager",
                ["red", "blue", "", "red", "blue"],
            ),
            ("combinatorial_sampler_manager", ["red", "blue", ""]),
        ],
    )
    def test_variant_with_blank(
        self,
        sampler_manager: str,
        expected: list[str],
        request: FixtureRequest,
    ):
        manager: ConcreteSamplerManager = request.getfixturevalue(sampler_manager)
        sampler = manager._samplers[SamplingMethod.DEFAULT]

        template = "A {red|blue|} rose"

        if isinstance(sampler, RandomSampler):
            sampler._random.choices = mock.Mock()
            sampler._random.choices.side_effect = [
                [LiteralCommand(v)] for v in expected
            ]
            prompts = manager.sample_prompts(template, 5)
        else:
            prompts = manager.sample_prompts(template, 5)

        expected_sentences = [f"A {e} rose" for e in expected]

        assert list(prompts) == expected_sentences

    @pytest.mark.parametrize(
        ("sampler_manager", "expected"),
        [
            (
                "random_sampler_manager",
                [
                    "A red circle",
                    "A green square",
                    "A red square",
                    "A green square",
                    "A green square",
                ],
            ),
            (
                "cyclical_sampler_manager",
                [
                    "A red square",
                    "A green circle",
                    "A red square",
                    "A green circle",
                    "A red square",
                ],
            ),
            (
                "combinatorial_sampler_manager",
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
        manager: ConcreteSamplerManager = request.getfixturevalue(sampler_manager)
        sampler = manager._samplers[SamplingMethod.DEFAULT]

        template = "A {red|green} {square|circle}"

        if isinstance(sampler, RandomSampler):
            split = [v.split() for v in expected]
            _, colours, shapes = zip(*split)
            random_choices = []

            for colour, shape in zip(colours, shapes):
                random_choices.append([LiteralCommand(colour)])
                random_choices.append([LiteralCommand(shape)])

            sampler._random.choices = mock.Mock()
            sampler._random.choices.side_effect = random_choices
            prompts = manager.sample_prompts(template, 5)
        else:
            prompts = manager.sample_prompts(template, 5)

        prompts = manager.sample_prompts(template, 5)
        assert list(prompts) == expected

    @pytest.mark.parametrize(
        ("sampler_manager", "expected"),
        [
            (
                "random_sampler_manager",
                [
                    "A red,green square",
                    "A green,red circle",
                    "A red,green square",
                    "A red,green square",
                    "A red,green square",
                ],
            ),
            (
                "cyclical_sampler_manager",
                [
                    "A red,green square",
                    "A green,red circle",
                    "A red,green square",
                    "A green,red circle",
                    "A red,green square",
                ],
            ),
            (
                "combinatorial_sampler_manager",
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
        manager: ConcreteSamplerManager = request.getfixturevalue(sampler_manager)
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

            sampler._random.choices = mock.Mock()
            sampler._random.choices.side_effect = random_choices
            prompts = manager.sample_prompts(template, 5)
        else:
            prompts = manager.sample_prompts(template, 5)

        assert list(prompts) == expected

    @pytest.mark.parametrize(
        ("sampler_manager", "expected"),
        [
            (
                "random_sampler_manager",
                [
                    "A red,green square",
                    "A red square",
                    "A red,green square",
                    "A red,green square",
                    "A red,green square",
                ],
            ),
            (
                "cyclical_sampler_manager",
                [
                    "A red square",
                    "A green square",
                    "A blue square",
                    "A red,green square",
                    "A red,blue square",
                ],
            ),
            (
                "combinatorial_sampler_manager",
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
        manager: ConcreteSamplerManager = request.getfixturevalue(sampler_manager)
        sampler = manager._samplers[SamplingMethod.DEFAULT]

        template = "A {1-2$$red|green|blue} square"
        prompts = manager.sample_prompts(template, 5)

        if isinstance(sampler, RandomSampler):
            split = [v.split() for v in expected]
            _, colours, _ = zip(*split)
            colour_pairs = [c.split(",") for c in colours]
            random_choices = []

            for pair in colour_pairs:
                for p in pair:
                    random_choices.append([LiteralCommand(p)])

            sampler._random.choices = mock.Mock()
            sampler._random.choices.side_effect = random_choices
            sampler._random.randint = mock.Mock()
            sampler._random.randint.side_effect = [2, 1, 2, 2, 2]

            prompts = manager.sample_prompts(template, 5)
        else:
            prompts = manager.sample_prompts(template, 5)

        assert list(prompts) == expected
