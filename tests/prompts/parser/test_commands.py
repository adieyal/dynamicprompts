import itertools
from typing import List

import pytest
from dynamicprompts.commands import (
    Command,
    LiteralCommand,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)

from tests.prompts.consts import ONE_TWO_THREE


@pytest.fixture
def literals() -> List[LiteralCommand]:
    return [LiteralCommand("hello"), LiteralCommand("world")]


class TestSequence:
    def test_length(self, literals: List[Command]):
        sequence = SequenceCommand(literals)
        assert len(sequence) == 2

    def test_getitem(self, literals: List[Command]):
        sequence = SequenceCommand(literals)
        assert sequence[0] == literals[0]
        assert sequence[1] == literals[1]


class TestLiteral:
    def test_prompts(self):
        command = LiteralCommand("test")
        assert command.literal == "test"

    def test_combine_literal_commands(self, literals):
        l3 = literals[0] + literals[1]
        assert l3.literal == "hello world"

    def test_error_combining_incompatible_commands(self):
        with pytest.raises(TypeError):
            _ = LiteralCommand("Hello") + VariantCommand.from_literals_and_weights(
                ["world"],
            )


class TestVariant:
    def test_length(self, literals: List[LiteralCommand]):
        variant_command = VariantCommand(literals)
        assert len(variant_command) == 2

    def test_getitem(self, literals: List[LiteralCommand]):
        variant_command = VariantCommand(literals)
        assert variant_command[0] == literals[0]
        assert variant_command[1] == literals[1]

    def test_combinations(self):
        variant_command = VariantCommand.from_literals_and_weights(ONE_TWO_THREE)
        assert [
            v.literal for v, in variant_command.get_value_combinations(1)
        ] == ONE_TWO_THREE
        assert [
            (a.literal, b.literal)
            for (a, b) in variant_command.get_value_combinations(2)
        ] == list(itertools.product(ONE_TWO_THREE, ONE_TWO_THREE))

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


class TestWildcard:
    def test_init_with_str(self):
        l1 = WildcardCommand("hello")
        assert l1.wildcard == "hello"
