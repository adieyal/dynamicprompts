from typing import cast
from unittest import mock

import pytest
from dynamicprompts.parser.commands import (
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
    @pytest.mark.parametrize(
        "input",
        [
            "hello world",
            "good-bye world",
            "good_bye world",
            "I, love. punctuation",
            "Test änderō",  # accents
            "Test [low emphasis]",  # square brackets
            "Test [low emphasis:0.4]",  # square brackets with weight
            "Test (high emphasis)",  # round brackets
            "Test (high emphasis:0.4)",  # round brackets with weight
        ],
    )
    def test_literal_characters(self, parser: Parser, input: str):
        sequence = parser.parse(input)
        assert len(sequence) == 1
        (literal,) = sequence  # will fail if len != 1
        assert literal.literal == input

    @pytest.mark.parametrize(
        "input",
        [
            "colours",
            "path/to/colours",
            "änder",
        ],
    )
    def test_wildcard(self, parser: Parser, input: str):
        sequence = parser.parse(f"__{input}__")
        (wildcard_command,) = sequence
        assert isinstance(wildcard_command, WildcardCommand)
        assert wildcard_command.wildcard == input

    def test_two_wildcards_adjancent(self, parser: Parser):
        sequence = parser.parse("__colours__ __colours__")
        assert len(sequence) == 3

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
            "{My favourite colour is __colour__ and not __other_colour__|__colour__ is my favourite colour}",
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

    def test_variant_delimiter(self, parser: Parser):
        sequence = parser.parse("{2$$ and $$cat|dog|bird}")
        variant = cast(VariantCommand, sequence[0])

        assert variant.min_bound == 2
        assert variant.max_bound == 2

        assert variant.sep == " and "

        sequence = parser.parse("I love {2$$|$$green|yellow|blue} roses")
        variant = cast(VariantCommand, sequence[1])
        assert len(variant) == 3
        assert variant[0][0] == "green"
        assert variant[1][0] == "yellow"
        assert variant[2][0] == "blue"

        assert variant.sep == "|"

        with pytest.raises(ParseException):
            sequence = parser.parse("{2$$ $ $$cat|dog|bird}")

        sequence = parser.parse("{2$$  $$cat|dog|bird}")

    def test_range_sd_issue_223(self, parser: Parser):
        # > {0-1$$a|b|c|d} would return nothing or one item. 0-1 could also be 0-3 etc.
        # > Since 2.52, if the random number picker lands on 0, instead of returning an empty set,
        # > the parser just stops and kicks out whatever it has, which results in a broken prompt.
        # https://github.com/adieyal/sd-dynamic-prompts/issues/223
        sequence = parser.parse(r"{0-1$$a|b|c|d}")
        var = sequence[0]
        assert isinstance(var, VariantCommand)
        assert var.min_bound == 0
        assert var.max_bound == 1

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
