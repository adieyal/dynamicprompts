from __future__ import annotations

from typing import cast

import pytest
from dynamicprompts.commands import (
    Command,
    LiteralCommand,
    SamplingMethod,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.utils import cross

from tests.consts import ONE_TWO_THREE


@pytest.fixture
def literals() -> list[str]:
    return ["hello", "world"]


class TestSequence:
    def test_length(self, literals: list[str | Command]):
        sequence = SequenceCommand.from_literals(literals)
        assert len(sequence) == 2

    def test_getitem(self, literals: list[str | Command]):
        sequence = SequenceCommand.from_literals(literals)
        assert cast(LiteralCommand, sequence[0]).literal == literals[0]
        assert cast(LiteralCommand, sequence[1]).literal == literals[1]

    @pytest.mark.parametrize(
        ("parent_sampling_method", "child_sampling_method", "expected_sampling_method"),
        [
            (
                SamplingMethod.COMBINATORIAL,
                SamplingMethod.COMBINATORIAL,
                SamplingMethod.COMBINATORIAL,
            ),
            (
                SamplingMethod.COMBINATORIAL,
                SamplingMethod.RANDOM,
                SamplingMethod.RANDOM,
            ),
            (
                SamplingMethod.COMBINATORIAL,
                SamplingMethod.CYCLICAL,
                SamplingMethod.CYCLICAL,
            ),
            (
                SamplingMethod.COMBINATORIAL,
                SamplingMethod.DEFAULT,
                SamplingMethod.COMBINATORIAL,
            ),
            (
                SamplingMethod.RANDOM,
                SamplingMethod.COMBINATORIAL,
                SamplingMethod.RANDOM,
            ),
            (SamplingMethod.RANDOM, SamplingMethod.RANDOM, SamplingMethod.RANDOM),
            (SamplingMethod.RANDOM, SamplingMethod.CYCLICAL, SamplingMethod.CYCLICAL),
            (SamplingMethod.RANDOM, SamplingMethod.DEFAULT, SamplingMethod.RANDOM),
            (
                SamplingMethod.CYCLICAL,
                SamplingMethod.COMBINATORIAL,
                SamplingMethod.CYCLICAL,
            ),
            (SamplingMethod.CYCLICAL, SamplingMethod.RANDOM, SamplingMethod.RANDOM),
            (SamplingMethod.CYCLICAL, SamplingMethod.CYCLICAL, SamplingMethod.CYCLICAL),
            (SamplingMethod.CYCLICAL, SamplingMethod.DEFAULT, SamplingMethod.CYCLICAL),
        ],
    )
    def test_propagation(
        self,
        parent_sampling_method: SamplingMethod,
        child_sampling_method: SamplingMethod,
        expected_sampling_method: SamplingMethod,
    ):
        commands: list[str | Command] = [
            LiteralCommand("literal", sampling_method=child_sampling_method),
            VariantCommand.from_literals_and_weights(
                ["opt1", "opt2"],
                sampling_method=child_sampling_method,
            ),
            WildcardCommand("colors*", sampling_method=child_sampling_method),
            SequenceCommand.from_literals(
                ["seq1", "seq2"],
                sampling_method=child_sampling_method,
            ),
        ]

        seq = SequenceCommand.from_literals(
            commands,
            sampling_method=parent_sampling_method,
        )
        seq.propagate_sampling_method(parent_sampling_method)

        for token in seq.tokens:
            assert token.sampling_method == expected_sampling_method


class TestLiteral:
    def test_prompts(self):
        command = LiteralCommand("test")
        assert command.literal == "test"

    def test_combine_literal_commands(self, literals):
        l3 = LiteralCommand(literals[0]) + LiteralCommand(literals[1])
        assert l3.literal == "hello world"

    def test_error_combining_incompatible_commands(self):
        with pytest.raises(TypeError):
            _ = LiteralCommand("Hello") + VariantCommand.from_literals_and_weights(
                ["world"],
            )


class TestVariant:
    def test_length(self, literals: list[str]):
        variant_command = VariantCommand.from_literals_and_weights(literals)
        assert len(variant_command) == 2

    def test_getitem(self, literals: list[str]):
        variant_command = VariantCommand.from_literals_and_weights(literals)
        assert variant_command[0].value == LiteralCommand(literals[0])
        assert variant_command[1].value == LiteralCommand(literals[1])

    def test_combinations(self):
        variant_command = VariantCommand.from_literals_and_weights(ONE_TWO_THREE)

        assert [
            v.literal for v, in variant_command.get_value_combinations(1)
        ] == ONE_TWO_THREE

        assert [
            (a.literal, b.literal)
            for (a, b) in variant_command.get_value_combinations(2)
        ] == list(cross(ONE_TWO_THREE, ONE_TWO_THREE))

    def test_range(self):
        variant_command = VariantCommand.from_literals_and_weights(
            ONE_TWO_THREE,
            min_bound=-1,
            max_bound=10,
        )
        assert variant_command.min_bound == 0  # check that negative values are clamped

        variant_command = VariantCommand.from_literals_and_weights(
            ONE_TWO_THREE,
            min_bound=2,
            max_bound=1,
        )
        assert variant_command.min_bound == 1
        assert variant_command.max_bound == 2

    def test_sampling_method(self, literals: list[str]):
        variant_command = VariantCommand.from_literals_and_weights(literals)
        assert variant_command.sampling_method == SamplingMethod.DEFAULT

        variant_command = VariantCommand.from_literals_and_weights(ONE_TWO_THREE)
        assert variant_command.sampling_method == SamplingMethod.DEFAULT

        variant_command = VariantCommand.from_literals_and_weights(
            ONE_TWO_THREE,
            sampling_method=SamplingMethod.RANDOM,
        )
        assert variant_command.sampling_method == SamplingMethod.RANDOM

        variant_command = VariantCommand.from_literals_and_weights(
            ONE_TWO_THREE,
            sampling_method=SamplingMethod.COMBINATORIAL,
        )
        assert variant_command.sampling_method == SamplingMethod.COMBINATORIAL


class TestWildcard:
    def test_init_with_str(self):
        l1 = WildcardCommand("hello")
        assert l1.wildcard == "hello"

    def test_sampling_method(self):
        l1 = WildcardCommand("hello")
        assert l1.sampling_method == SamplingMethod.DEFAULT

        l2 = WildcardCommand("hello", sampling_method=SamplingMethod.RANDOM)
        assert l2.sampling_method == SamplingMethod.RANDOM

        l3 = WildcardCommand("hello", sampling_method=SamplingMethod.COMBINATORIAL)
        assert l3.sampling_method == SamplingMethod.COMBINATORIAL

        l4 = WildcardCommand("hello", sampling_method=SamplingMethod.CYCLICAL)
        assert l4.sampling_method == SamplingMethod.CYCLICAL
