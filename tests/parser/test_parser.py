from __future__ import annotations

from typing import cast

import pytest
from dynamicprompts.commands import (
    LiteralCommand,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.commands.base import Command, SamplingMethod
from dynamicprompts.commands.variable_commands import (
    VariableAccessCommand,
    VariableAssignmentCommand,
)
from dynamicprompts.parser.config import ParserConfig
from dynamicprompts.parser.parse import (
    _create_weight_parser,
    parse,
)
from pyparsing import ParseException


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
            "Unmatched } bracket",
        ],
    )
    def test_literal_characters(self, input: str):
        literal = parse(input)
        assert isinstance(literal, LiteralCommand)
        assert literal.literal == input

    @pytest.mark.parametrize(
        "input",
        [
            "colours",
            "path/to/colours",
            "änder",
        ],
    )
    def test_wildcard(self, input: str):
        wildcard_command = parse(f"__{input}__")
        assert isinstance(wildcard_command, WildcardCommand)
        assert wildcard_command.wildcard == input
        assert wildcard_command.sampling_method is None

    @pytest.mark.parametrize(
        "input, expected_commands",
        [
            (
                "path/to/${subject}",
                [
                    LiteralCommand("path/to/"),
                    VariableAccessCommand("subject", LiteralCommand("subject")),
                ],
            ),
            (
                "${pallette}_colours",
                [
                    VariableAccessCommand("pallette", LiteralCommand("pallette")),
                    LiteralCommand("_colours"),
                ],
            ),
            (
                "${pallette:warm}_colours",
                [
                    VariableAccessCommand("pallette", LiteralCommand("warm")),
                    LiteralCommand("_colours"),
                ],
            ),
            (
                "locations/${room: dining room }/furniture",
                [
                    LiteralCommand("locations/"),
                    VariableAccessCommand("room", LiteralCommand("dining room")),
                    LiteralCommand("/furniture"),
                ],
            ),
            (
                "light/source/{indoor|outdoor}",
                [
                    LiteralCommand("light/source/"),
                    VariantCommand.from_literals_and_weights(["indoor", "outdoor"]),
                ],
            ),
        ],
    )
    def test_wildcard_dynamic(self, input: str, expected_commands: list[Command]):
        wildcard_command = parse(f"__{input}__")
        assert isinstance(wildcard_command, WildcardCommand)
        assert isinstance(wildcard_command.wildcard, SequenceCommand)
        wildcard_sequence = cast(SequenceCommand, wildcard_command.wildcard)
        assert wildcard_sequence.tokens == expected_commands
        assert wildcard_command.sampling_method is None

    @pytest.mark.parametrize(
        "input, sampling_method, wildcard",
        [
            ("colours", None, "colours"),
            ("~path/to/colours", SamplingMethod.RANDOM, "path/to/colours"),
            ("!änder", SamplingMethod.COMBINATORIAL, "änder"),
            ("@änder", SamplingMethod.CYCLICAL, "änder"),
        ],
    )
    def test_sampling_method(
        self,
        input: str,
        sampling_method: SamplingMethod | None,
        wildcard: str,
    ):
        wildcard_command = parse(f"__{input}__")
        assert isinstance(wildcard_command, WildcardCommand)
        assert wildcard_command.wildcard == wildcard
        assert wildcard_command.sampling_method == sampling_method

    def test_two_wildcards_adjacent(self):
        sequence = parse("__colours__ __colours__")
        assert len(sequence) == 3

    def test_wildcard_adjactent_to_literal(self):
        literal, wildcard_command = parse(",__colours__")
        assert literal.literal == ","
        assert isinstance(wildcard_command, WildcardCommand)
        assert wildcard_command.wildcard == "colours"

        wildcard_command, literal = parse("__colours__ world")
        assert wildcard_command.wildcard == "colours"
        assert literal.literal == " world"

    def test_weight(self):
        weight = _create_weight_parser()
        with pytest.raises(ParseException):
            weight.parse_string("1")

        assert weight.parse_string("1::")[0] == 1.0
        assert weight.parse_string("0.25::")[0] == 0.25

    def test_basic_variant(self):
        variant = parse("{cat|dog}")
        assert isinstance(variant, VariantCommand)
        assert len(variant) == 2
        assert variant.weights == [1.0, 1.0]
        values = variant.values
        assert all(isinstance(v, LiteralCommand) for v in values)
        assert values[0].literal == "cat"
        assert values[1].literal == "dog"

    @pytest.mark.parametrize(
        "input, sampling_method",
        [
            ("{red|green|blue}", None),
            ("{~red|green|blue}", SamplingMethod.RANDOM),
            ("{!red|green|blue}", SamplingMethod.COMBINATORIAL),
            ("{!__test/colours__}", SamplingMethod.COMBINATORIAL),
            ("{~1-3$$ and $$red|green|blue}", SamplingMethod.RANDOM),
            ("{~0.2::red|0.4::green|0.6::blue}", SamplingMethod.RANDOM),
            ("{@0.2::red|0.4::green|0.6::blue}", SamplingMethod.CYCLICAL),
        ],
    )
    def test_variant_with_sampling_method(self, input, sampling_method):
        variant = parse(input)
        assert isinstance(variant, VariantCommand)
        assert variant.sampling_method == sampling_method

    def test_variant_with_different_characters(self):
        variant = parse("{new york|washing-ton!|änder}")
        assert isinstance(variant, VariantCommand)
        assert [v.literal for v in variant.values] == [
            "new york",
            "washing-ton!",
            "änder",
        ]

    def test_variant_with_blank(self):
        variant = parse("{|red|blue}")
        assert isinstance(variant, VariantCommand)
        a, b, c = variant.values
        assert len(a) == 0
        assert b.literal == "red"
        assert c.literal == "blue"

    def test_variant_breaks_without_closing_bracket(self):
        with pytest.raises(ParseException):
            parse("{cat|dog")

    def test_variant_with_wildcard(self):
        variant = parse("{__test/colours__|washington}")
        assert isinstance(variant, VariantCommand)
        wildcard_command, washington = variant.values
        assert isinstance(wildcard_command, WildcardCommand)
        assert wildcard_command.wildcard == "test/colours"
        assert isinstance(washington, LiteralCommand)
        assert washington.literal == "washington"

    def test_variant_sequences(self):
        variant = parse(
            "{My favourite colour is __colour__ and not __other_colour__|__colour__ is my favourite colour}",
        )
        assert isinstance(variant, VariantCommand)
        assert len(variant) == 2
        sequence1, sequence2 = variant.values

        assert len(sequence1) == 4
        literal1, wildcard1, literal2, wildcard2 = sequence1
        assert isinstance(literal1, LiteralCommand)
        assert literal1.literal == "My favourite colour is "
        assert isinstance(wildcard1, WildcardCommand)
        assert wildcard1.wildcard == "colour"
        assert isinstance(literal2, LiteralCommand)
        assert literal2.literal == " and not "
        assert isinstance(wildcard2, WildcardCommand)
        assert wildcard2.wildcard == "other_colour"

        wildcard3, literal3 = sequence2
        assert isinstance(wildcard3, WildcardCommand)
        assert wildcard3.wildcard == "colour"
        assert isinstance(literal3, LiteralCommand)
        assert literal3.literal == " is my favourite colour"

    def test_variant_with_nested_variant(self):
        variant = parse("{__test/colours__|{__test/shapes__|washington}}")
        assert isinstance(variant, VariantCommand)
        assert len(variant) == 2
        (wildcard, nested_variant) = variant.values
        assert isinstance(wildcard, WildcardCommand)
        assert wildcard.wildcard == "test/colours"
        assert isinstance(nested_variant, VariantCommand)
        assert len(nested_variant) == 2
        nested_wildcard, literal = nested_variant.values
        assert isinstance(nested_wildcard, WildcardCommand)
        assert nested_wildcard.wildcard == "test/shapes"
        assert isinstance(literal, LiteralCommand)
        assert literal.literal == "washington"

    @pytest.mark.parametrize(
        "input, weights",
        [
            ("{1::cat|2::dog|3::bird} test", [1, 2, 3]),
            ("{0.2::cat|0.3::dog|0.4::bird} test", [0.2, 0.3, 0.4]),
            ("{1::cat|dog|3::bird} test", [1, 1, 3]),  # default weight
        ],
    )
    def test_variant_with_weights(self, input, weights):
        variant, literal = parse(input)
        assert isinstance(variant, VariantCommand)
        assert variant.weights == weights
        assert [v.literal for v in variant.values] == ["cat", "dog", "bird"]

    @pytest.mark.parametrize(
        "input, min_bound, max_bound",
        [
            ("{2$$cat|dog|bird}", 2, 2),
            ("{1-2$$cat|dog|bird}", 1, 2),
            ("{1-3$$cat|dog|bird}", 1, 3),
            ("{-2$$cat|dog|bird}", 1, 2),
            (
                "{0-1$$a|b|c|d}",
                0,
                1,
            ),  # https://github.com/adieyal/sd-dynamic-prompts/issues/223
            ("{!1-2$$cat|dog|bird}", 1, 2),
            ("{~1-2$$cat|dog|bird}", 1, 2),
            ("{2-$$cat|dog|bird}", 2, 3),
            ("{0-$$cat|dog|bird}", 0, 3),
        ],
    )
    def test_range(self, input, min_bound, max_bound):
        variant = parse(input)
        assert isinstance(variant, VariantCommand)
        assert variant.min_bound == min_bound
        assert variant.max_bound == max_bound
        assert variant.separator == ","

    def test_variant_delimiter(self):
        variant = parse("{2$$ and $$cat|dog|bird}")
        assert isinstance(variant, VariantCommand)

        assert variant.min_bound == 2
        assert variant.max_bound == 2
        assert variant.separator == " and "

        proclamation, variant, flower = parse(
            "I love {2$$|$$green|yellow|blue} roses",
        )
        assert isinstance(variant, VariantCommand)
        assert [v.literal for v in variant.values] == [
            "green",
            "yellow",
            "blue",
        ]
        assert variant.separator == "|"

        with pytest.raises(ParseException):
            parse(
                "{2$$ $ $$cat|dog|bird}",
            )  # A dollar sign is not a valid separator

        parse("{2$$  $$cat|dog|bird}")  # A space is a valid separator

    def test_variants_adjacent(self):
        sequence = parse("{2$$cat|dog|bird}{3$$red|blue|green}")
        assert len(sequence) == 2
        assert isinstance(sequence[0], VariantCommand)
        assert isinstance(sequence[1], VariantCommand)
        variant1, variant2 = sequence

        assert variant1.min_bound == 2
        assert variant1.max_bound == 2
        assert variant1.separator == ","
        assert [v.literal for v in variant1.values] == ["cat", "dog", "bird"]

        assert variant2.min_bound == 3
        assert variant2.max_bound == 3
        assert variant2.separator == ","
        assert [v.literal for v in variant2.values] == ["red", "blue", "green"]

    def test_comments(self):
        prompt = """
        one
        two
        three # comment
        # A comment
        {cat|dog|bird} # another comment
        __wildcard_comment__# another comment
        five
        """

        sequence = parse(prompt)
        assert len(sequence) == 5
        one_two_three, variant, whitespace, wildcard, five = sequence

        assert (
            one_two_three.literal
            == "\n        one\n        two\n        three  \n        "
        )
        assert isinstance(variant, VariantCommand)
        assert [v.literal for v in variant.values] == ["cat", "dog", "bird"]
        assert whitespace.literal == "\n        "
        assert isinstance(wildcard, WildcardCommand)
        assert wildcard.wildcard == "wildcard_comment"
        assert five.literal == "\n        five\n        "

    @pytest.mark.parametrize(
        "input",
        [
            "[cat|dog]",  # alternating words
            "[cat:dog:0.25]",  # prompt editing
        ],
    )
    def test_a1111_special_syntax_intact(self, input):
        assert parse(input).literal == input

    @pytest.mark.parametrize(
        ("input", "expected_count"),
        [
            ("A literal sentence", 1),
            ("{RED|GREEN|BLUE}", 4),
            ("__wildcard__", 1),
            ("{A|B|C} {D|E|g}", 10),
        ],
    )
    def test_deep_propagation(self, input: str, expected_count: int):
        def check_children(parent: Command) -> int:
            total_count = 1

            if isinstance(parent, VariantCommand):
                variant = cast(VariantCommand, parent)
                for value in variant.values:
                    child_count = check_children(value)
                    total_count += child_count
            elif isinstance(parent, SequenceCommand):
                sequence = cast(SequenceCommand, parent)
                for token in sequence.tokens:
                    child_count = check_children(token)
                    total_count += child_count

            return total_count

        command = parse(input)
        assert check_children(command) == expected_count

    @pytest.mark.parametrize(
        ("variant_start", "variant_end", "template"),
        [
            ("<", ">", "some literal string <A|B|__some/wildcard__>"),
            ("_", "_", "some literal string _A|B|__some/wildcard___"),
            (":", ":", "some literal string :A|B|__some/wildcard__:"),
            ("&", "&", "some literal string &A|B|__some/wildcard__&"),
            (
                "[",
                "]",
                "some literal string [A|B|__some/wildcard__]",
            ),  # This also tests that regex is escaped correctly
            ("<<:", ":>>", "some literal string <<:A|B|__some/wildcard__:>>"),
        ],
    )
    def test_alternative_braces(self, variant_start: str, variant_end, template: str):
        config = ParserConfig(variant_start=variant_start, variant_end=variant_end)
        sequence = cast(SequenceCommand, parse(template, parser_config=config))
        variant = cast(VariantCommand, sequence[1])

        assert variant.values[0].literal == "A"
        assert variant.values[1].literal == "B"
        assert variant.values[2].wildcard == "some/wildcard"

    @pytest.mark.parametrize(
        ("wildcard_wrap", "template"),
        [
            (r"&", r"some literal string {A|B|&some/wildcard&}"),
            (r"@@", r"some literal string {A|B|@@some/wildcard@@}"),
            (r"!!", r"some literal string {A|B|!!some/wildcard!!}"),
            (r"..", r"some literal string {A|B|..some/wildcard..}"),
            (r"~~", r"some literal string {A|B|~~some/wildcard~~}"),
            (r"**", r"some literal string {A|B|**some/wildcard**}"),
            (r"___", r"some literal string {A|B|___some/wildcard___}"),
        ],
    )
    def test_alternative_wildcard_wrap(self, wildcard_wrap: str, template: str):
        config = ParserConfig(wildcard_wrap=wildcard_wrap)
        sequence = cast(SequenceCommand, parse(template, parser_config=config))
        variant = cast(VariantCommand, sequence[1])

        assert variant.values[0].literal == "A"
        assert variant.values[1].literal == "B"
        assert variant.values[2].wildcard == "some/wildcard"

    @pytest.mark.parametrize("immediate", (False, True), ids=("delayed", "immediate"))
    @pytest.mark.parametrize(
        "overwrite",
        (False, True),
        ids=("preserve existing value", "overwrite existing value"),
    )
    def test_variable_commands(self, immediate: bool, overwrite: bool):
        op = "?" if not overwrite else ""
        op += "=!" if immediate else "="
        sequence = cast(
            SequenceCommand,
            parse(f"${{animal {op} cat}} the animal is ${{animal:dog}}"),
        )
        assert len(sequence) == 3
        ass = sequence[0]
        assert isinstance(ass, VariableAssignmentCommand)
        assert ass.name == "animal"
        assert ass.value == LiteralCommand("cat")
        assert ass.overwrite == overwrite
        assert ass.immediate == immediate
        acc = sequence[2]
        assert isinstance(acc, VariableAccessCommand)
        assert acc.name == "animal"
        assert acc.default == LiteralCommand("dog")

    @pytest.mark.parametrize(
        "var_spec, expected_vars",
        [
            ("", {}),
            ("(animal=bear)", {"animal": LiteralCommand("bear")}),
            (
                "(animal=fox,color=red)",
                {"animal": LiteralCommand("fox"), "color": LiteralCommand("red")},
            ),
            (
                "(color={A|B|C})",
                {"color": VariantCommand.from_literals_and_weights(list("ABC"))},
            ),
        ],
    )
    def test_wildcard_variable_shorthand(self, var_spec: str, expected_vars: dict):
        cmd = parse(f"__foo{var_spec}__")
        assert isinstance(cmd, WildcardCommand)
        assert cmd.wildcard == "foo"
        assert cmd.variables == expected_vars
