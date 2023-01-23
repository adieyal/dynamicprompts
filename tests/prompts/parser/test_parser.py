from typing import cast
from unittest import mock

import pytest
from dynamicprompts.parser.commands import (
    Command,
    LiteralCommand,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.parser.parse import (
    ActionBuilder,
    Parser,
)
from pyparsing import ParseException


@pytest.fixture
def wildcard_manager():
    return mock.Mock()


@pytest.fixture
def parser(wildcard_manager) -> Parser:
    return Parser(ActionBuilder(wildcard_manager))


class TestParser:
    def test_basic_parser(self, parser: Parser):
        sequence = parser.parse("hello world")

        assert type(sequence) == SequenceCommand
        assert len(sequence) == 1
        assert type(sequence[0]) == LiteralCommand
        assert sequence[0] == "hello world"

    def test_literal_characters(self, parser: Parser):
        sequence = parser.parse("good-bye world")
        assert len(sequence) == 1
        assert sequence[0] == "good-bye world"

        sequence = parser.parse("good_bye world")
        assert len(sequence) == 1
        assert sequence[0] == "good_bye world"

        sequence = parser.parse("I, love. punctuation")
        assert len(sequence) == 1
        variant = cast(VariantCommand, sequence)
        assert variant[0] == "I, love. punctuation"

    def test_literal_with_accents(self, parser: Parser):
        sequence = parser.parse("Test änderō")
        assert len(sequence) == 1
        assert sequence[0] == "Test änderō"

    def test_literal_with_square_brackets(self, parser: Parser):
        sequence = parser.parse("Test [low emphasis]")
        assert len(sequence) == 1
        assert sequence[0] == "Test [low emphasis]"

        sequence = parser.parse("Test [low emphasis:0.4]")
        assert len(sequence) == 1
        assert sequence[0] == "Test [low emphasis:0.4]"

    def test_literal_with_round_brackets(self, parser: Parser):
        sequence = parser.parse("Test (high emphasis)")
        assert len(sequence) == 1
        assert sequence[0] == "Test (high emphasis)"

        sequence = parser.parse("Test (high emphasis:0.4)")
        assert len(sequence) == 1
        assert sequence[0] == "Test (high emphasis:0.4)"

    def test_wildcard(self, parser: Parser):
        sequence = parser.parse("__colours__")
        assert len(sequence) == 1

        wildcard_command = sequence[0]
        assert type(wildcard_command) == WildcardCommand
        wildcard_command = cast(WildcardCommand, wildcard_command)
        assert wildcard_command.wildcard == "colours"

        sequence = parser.parse("__path/to/colours__")
        assert len(sequence) == 1

        wildcard_command = sequence[0]
        assert type(wildcard_command) == WildcardCommand
        wildcard_command = cast(WildcardCommand, wildcard_command)
        assert wildcard_command.wildcard == "path/to/colours"

    def test_two_wildcards_adjancent(self, parser: Parser):
        sequence = parser.parse("__colours__ __colours__")
        assert len(sequence) == 3

    def test_wildcard_with_accents(self, parser: Parser):
        sequence = parser.parse("__änder__")
        assert len(sequence) == 1
        wildcard_command = cast(WildcardCommand, sequence[0])
        assert wildcard_command.wildcard == "änder"

    def test_wildcard_adjactent_to_literal(self, parser: Parser):
        sequence = parser.parse(",__colours__")

        assert len(sequence) == 2
        assert sequence[0] == ","
        wildcard_command = cast(WildcardCommand, sequence[1])
        assert wildcard_command.wildcard == "colours"

        sequence = parser.parse("__colours__ world")
        assert len(sequence) == 2
        wildcard_command = cast(WildcardCommand, sequence[0])
        assert wildcard_command.wildcard == "colours"

        assert sequence[1] == " world"

    def test_weight(self, parser: Parser):
        weight = parser._configure_weight()
        with pytest.raises(ParseException):
            weight.parse_string("1")

        assert weight.parse_string("1::")[0] == 1.0
        assert weight.parse_string("0.25::")[0] == 0.25

    def test_basic_variant(self, parser: Parser):
        sequence = parser.parse("{cat|dog}")

        assert len(sequence) == 1
        assert type(sequence[0]) == VariantCommand

        variant = cast(VariantCommand, sequence[0])
        assert len(variant) == 2
        assert type(variant[0]) == SequenceCommand

        sequence1 = cast(SequenceCommand, variant[0])
        assert len(sequence1) == 1
        assert sequence1[0] == LiteralCommand("cat")

        sequence2 = cast(SequenceCommand, variant[1])
        assert len(sequence2) == 1
        assert sequence2[0] == LiteralCommand("dog")

    def test_variant_with_different_characters(self, parser: Parser):
        sequence = parser.parse("{new york|washing-ton!|änder}")

        variant = cast(VariantCommand, sequence[0])
        assert len(variant) == 3
        assert variant[0][0] == "new york"
        assert variant[1][0] == "washing-ton!"
        assert variant[2][0] == "änder"

    def test_variant_with_blank(self, parser: Parser):
        sequence = parser.parse("{|red|blue}")
        variant = cast(VariantCommand, sequence[0])
        assert len(variant) == 3
        assert len(variant[0]) == 0

        assert variant[1][0] == "red"
        assert variant[2][0] == "blue"

    def test_variant_breaks_without_closing_bracket(self, parser: Parser):

        with pytest.raises(ParseException):
            parser.parse("{cat|dog")

    def test_variant_breaks_without_opening_bracket(self, parser: Parser):
        with pytest.raises(ParseException):
            parser.parse("cat|dog}")

    def test_variant_with_wildcard(self, parser: Parser):
        sequence = parser.parse("{__test/colours__|washington}")
        assert len(sequence) == 1
        assert type(sequence[0]) == VariantCommand
        variant = cast(VariantCommand, sequence[0])

        wildcard_command = cast(WildcardCommand, variant[0][0])
        assert wildcard_command.wildcard == "test/colours"
        assert variant[1][0] == "washington"

    def test_variant_sequences(self, parser: Parser):

        sequence = parser.parse(
            "{My favourite colour is __colour__ and not __other_colour__|__colour__ is my favourite colour}"
        )
        assert len(sequence) == 1
        assert type(sequence[0]) == VariantCommand
        variant = cast(VariantCommand, sequence[0])

        assert len(variant) == 2

        sequence1 = variant[0]
        assert len(sequence1) == 4
        assert type(sequence1[0]) == LiteralCommand

        assert sequence1[0] == "My favourite colour is "

        assert type(sequence1[1]) == WildcardCommand
        wildcard_command = cast(WildcardCommand, sequence1[1])
        assert wildcard_command.wildcard == "colour"

        assert type(sequence1[2]) == LiteralCommand

        assert sequence1[2] == " and not "

        assert type(sequence1[3]) == WildcardCommand
        wildcard_command = cast(WildcardCommand, sequence1[3])
        assert wildcard_command.wildcard == "other_colour"

        sequence2 = variant[1]
        assert len(sequence2) == 2

        assert type(sequence2[0]) == WildcardCommand
        wildcard_command = cast(WildcardCommand, sequence2[0])
        assert wildcard_command.wildcard == "colour"

        assert type(sequence2[1]) == LiteralCommand

        assert sequence2[1] == " is my favourite colour"

    def test_variant_with_nested_variant(self, parser: Parser):
        sequence = parser.parse("{__test/colours__|{__test/colours__|washington}}")
        assert len(sequence) == 1
        assert type(sequence[0]) == VariantCommand
        variant = cast(VariantCommand, sequence[0])

        assert len(variant) == 2

        assert type(variant[0][0]) == WildcardCommand
        assert type(variant[1][0]) == VariantCommand

        nested_variant = cast(VariantCommand, variant[1][0])
        assert len(nested_variant) == 2
        assert type(nested_variant[0][0]) == WildcardCommand
        assert nested_variant[0][0].wildcard == "test/colours"

        assert type(nested_variant[1][0]) == LiteralCommand
        assert nested_variant[1][0] == "washington"

    def test_variant_with_weights(self, parser: Parser):

        sequence = parser.parse("{1::cat|2::dog|3::bird} test")

        variant = cast(VariantCommand, sequence[0])
        assert variant.weights[0] == 1
        assert variant.weights[1] == 2
        assert variant.weights[2] == 3

        assert variant[0][0] == "cat"
        assert variant[1][0] == "dog"
        assert variant[2][0] == "bird"

        sequence = parser.parse("{0.2::cat|0.3::dog|0.4::bird} test")

        variant = cast(VariantCommand, sequence[0])
        assert variant.weights[0] == 0.2
        assert variant.weights[1] == 0.3
        assert variant.weights[2] == 0.4

        assert variant[0][0] == "cat"
        assert variant[1][0] == "dog"
        assert variant[2][0] == "bird"

    def test_variant_with_defaultweights(self, parser: Parser):
        sequence = parser.parse("{1::cat|dog|3::bird} test")

        variant = cast(VariantCommand, sequence[0])
        assert variant.weights[0] == 1
        assert variant.weights[1] == 1
        assert variant.weights[2] == 3

    def test_range(self, parser: Parser):
        sequence = parser.parse("{2$$cat|dog|bird}")
        variant = cast(VariantCommand, sequence[0])

        assert variant.min_bound == 2
        assert variant.max_bound == 2
        assert variant.sep == ","

        sequence = parser.parse("{1-2$$cat|dog|bird}")
        variant = cast(VariantCommand, sequence[0])

        assert variant.min_bound == 1
        assert variant.max_bound == 2

        sequence = parser.parse("{1-$$cat|dog|bird}")
        variant = cast(VariantCommand, sequence[0])

        assert variant.min_bound == 1
        assert variant.max_bound == 3

        sequence = parser.parse("{-2$$cat|dog|bird}")
        variant = cast(VariantCommand, sequence[0])

        assert variant.min_bound == 1
        assert variant.max_bound == 2

        sequence = parser.parse("{2$$ and $$cat|dog|bird}")
        variant = cast(VariantCommand, sequence[0])

        assert variant.min_bound == 2
        assert variant.max_bound == 2

        assert variant.sep == " and "

    def test_comments(self, parser: Parser):

        prompt = """
        one
        two
        three # comment
        # A comment
        {cat|dog|bird} # another comment
        __wildcard_comment__# another comment
        five
        """

        sequence = parser.parse(prompt)
        assert len(sequence) == 5

        assert sequence[0] == "\n        one\n        two\n        three  \n        "

        assert isinstance(sequence[1], VariantCommand)
        variant = cast(VariantCommand, sequence[1])
        assert len(variant) == 3
        assert variant[0][0] == "cat"
        assert variant[1][0] == "dog"
        assert variant[2][0] == "bird"

        assert isinstance(sequence[2], LiteralCommand)
        assert sequence[2] == "\n        "
        assert isinstance(sequence[3], WildcardCommand)
        wildcard = cast(WildcardCommand, sequence[3])
        assert wildcard.wildcard == "wildcard_comment"

        assert sequence[4] == "\n        five\n        "

    def test_alternating_words(self, parser: Parser):

        sequence = parser.parse("[cat|dog]")
        assert len(sequence) == 1
        assert sequence[0] == "[cat|dog]"

    def test_prompt_editing(self, parser: Parser):

        prompt = "[cat:dog:0.25]"
        sequence = parser.parse(prompt)
        assert len(sequence) == 1
        assert sequence[0] == prompt
