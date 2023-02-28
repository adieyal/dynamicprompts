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

    def test_sampling_method(self):
        assert (
            VariantCommand.from_literals_and_weights(ONE_TWO_THREE).sampling_method
            is None
        )

        assert (
            VariantCommand.from_literals_and_weights(
                ONE_TWO_THREE,
                sampling_method=SamplingMethod.RANDOM,
            ).sampling_method
            == SamplingMethod.RANDOM
        )

        assert (
            VariantCommand.from_literals_and_weights(
                ONE_TWO_THREE,
                sampling_method=SamplingMethod.COMBINATORIAL,
            ).sampling_method
            == SamplingMethod.COMBINATORIAL
        )


class TestWildcard:
    def test_init_with_str(self):
        l1 = WildcardCommand("hello")
        assert l1.wildcard == "hello"

    def test_sampling_method(self):
        l1 = WildcardCommand("hello")
        assert l1.sampling_method is None

        l2 = WildcardCommand("hello", sampling_method=SamplingMethod.RANDOM)
        assert l2.sampling_method == SamplingMethod.RANDOM

        l3 = WildcardCommand("hello", sampling_method=SamplingMethod.COMBINATORIAL)
        assert l3.sampling_method == SamplingMethod.COMBINATORIAL

        l4 = WildcardCommand("hello", sampling_method=SamplingMethod.CYCLICAL)
        assert l4.sampling_method == SamplingMethod.CYCLICAL
