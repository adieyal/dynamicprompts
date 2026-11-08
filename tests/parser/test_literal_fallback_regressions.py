"""
Differential regression tests for the parser's literal-text fallback.

The corpus is run through CombinatorialPromptGenerator. Expected outputs are
main's (2475e31) unless the prompt is listed in INTENDED_DIFFERENCES.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Type, Union

import pytest
from dynamicprompts.commands import (
    LiteralCommand,
    SequenceCommand,
    WildcardCommand,
)
from dynamicprompts.commands.variable_commands import VariableAccessCommand
from dynamicprompts.generators import CombinatorialPromptGenerator
from dynamicprompts.parser.config import ParserConfig
from dynamicprompts.parser.parse import parse
from dynamicprompts.wildcards import WildcardManager
from pyparsing import ParseException

WILDCARDS = Path(__file__).parent.parent / "test_data" / "literal_fallback"
MAX_PROMPTS = 6

DEFAULT = ParserConfig()
ANGLE_VARIABLES = ParserConfig(variable_start="<<", variable_end=">>")
STAR_WILDCARDS = ParserConfig(wildcard_wrap="**")

Expected = Union[List[str], Type[Exception]]

# Main's outputs for the corpus, except that a missing wildcard now yields its
# text once in the combinatorial sampler instead of endlessly.
MAIN_OUTPUTS: dict[str, Expected] = {
    "x __${n:a}__": ["x a-val"],
    "__${n:a}__": ["a-val"],
    "x __{a|b}__": ["x a-val"],
    "{a|x __${n:b}__}": ["a", "x b-val"],
    "${n=a} x __${n}__": [" x a-val"],
    "x __c/${k:red}__": ["x c/red-val"],
    "x\n__a__": ["x\na-val"],
    "x __a__ y __b__": ["x a-val y b-val"],
    "%{a$$b}": ["ab"],
    "x %{a$$b}": ["x ab"],
    "{x %{a$$b}|y}": ["x ab", "y"],
    "x ${v=1}${v}": ["x 1"],
    "x ${v={a|b}} ${v}": ["x  a", "x  b"],
    "x ${v=a} ${v}": ["x  a"],
    "{2::a|b} __a__": ["a a-val", "b a-val"],
    "a\\": ["a\\"],
    "{a|b\\}": ["a", "b\\"],
    "{a\\}": ["a\\"],
    "__a\\b__": ["__a\\b__"],
    "x __a\\b__": ["x __a\\b__"],
    "a\\\\": ["a\\\\"],
    "\\__a__": ["\\a-val"],
    "x \\__a__": ["x \\a-val"],
    "__a(v=1)__": ["a-val"],
    "x __a(v=1)__": ["x a-val"],
    "x __a(v={p|q})__": ["x a-val"],
    "x __a(v=${n:z})__": ["x a-val"],
    "a, b, c": ["a, b, c"],
    "(a:1.1), [b], {c|d}": ["(a:1.1), [b], c", "(a:1.1), [b], d"],
    "x $$ y": ParseException,
    "{a$$b|c}": ParseException,
    "{2$$a|b|c}": ["a,b", "a,c", "b,a", "b,c", "c,a", "c,b"],
    "{1-2$$,$$a|b|c}": ["a", "b", "c", "a,b", "a,c", "b,a"],
    "x ${n:{p|q}}": ["x p", "x q"],
    "x__a__y": ["xa-valy"],
    "5$ and $5": ParseException,
    "50% {a|b}": ParseException,
    "{50%|60%}": ParseException,
    "x %{}": ParseException,
    "emoji \U0001f642 {a|b}": ["emoji \U0001f642 a", "emoji \U0001f642 b"],
    # 143: a # followed by text mid-line is literal, not a comment.
    "a #c\n{b|c}": ["a #c\nb", "a #c\nc"],
    "x __~a__": ["x a-val"],
    "x __@a__": ["x a-val"],
    "x {@a|b}": ["x a"],
    "__a__ __b__": ["a-val b-val"],
    "<a> __a__ <b>": ["<a> a-val <b>"],
    # The design proposal's probe cases.
    "a __ b": ParseException,
    "snake__case text": ParseException,
    # Kept as on main: inner edges are non-space, so the two `__` pair up.
    "snake__case and other__thing": ["snake__case and other__thing"],
    "<lora:foo__bar:1> __a__": ParseException,
    "<lora:foo__bar:1>, __a__ x__b__y": ParseException,
    "$tephanie $0 $10 50% 100% FREE": ParseException,
    "{$tephanie|50%}": ParseException,
    "x ${n:v} %{a$$b}": ["x v ab"],
    "${q=\\{lit\\}}${q}": ["\\lit\\"],
    "a \\{b\\} \\| \\$ \\q \\( \\\\": ParseException,
    "{a\\|b|c}": ["a\\", "b", "c"],
    "x ${n": ParseException,
    "x %{a": ParseException,
    "x ${n>z}": ParseException,
    "x __a(v=)__": ["x a-val"],
    "x __a(v=1,,)__": ["x a-val"],
    "x__y(z) __a__": ParseException,
    "__a(v=\\,1)__": ["a-val"],
    "__${n}(v=1)__": ["__n__"],
    "a # c\n{b|c}": ["a  \nb", "a  \nc"],
    "x\\__a__": ["x\\a-val"],
}

# Prompts that need a non-default ParserConfig, with main's outputs.
MAIN_OUTPUTS_WITH_CONFIG: list[tuple[str, ParserConfig, Expected]] = [
    ("x <<name>z>>", ANGLE_VARIABLES, ParseException),
    # Pre-existing bug, kept: the variant literal doesn't stop at `>>`.
    ("<lora:x> <<name:d>>", ANGLE_VARIABLES, ParseException),
    ("x **a** <lora:foo**bar:1> **b**", STAR_WILDCARDS, ParseException),
    ("x ** y", STAR_WILDCARDS, ParseException),
]

# Intended differences from main, by acceptance criterion.
INTENDED_DIFFERENCES: dict[str, Expected] = {
    # AC-03: `$`, `%` and `$$` that open no command are literal.
    "x $$ y": ["x $$ y"],
    "5$ and $5": ["5$ and $5"],
    "50% {a|b}": ["50% a", "50% b"],
    "{50%|60%}": ["50%", "60%"],
    "$tephanie $0 $10 50% 100% FREE": ["$tephanie $0 $10 50% 100% FREE"],
    "{$tephanie|50%}": ["$tephanie", "50%"],
    # AC-04: backslash escapes reserved characters, once.
    "a\\\\": ["a\\"],
    "\\__a__": ["__a__"],
    "x \\__a__": ["x __a__"],
    "x\\__a__": ["x__a__"],
    "${q=\\{lit\\}}${q}": ["{lit}"],
    "a \\{b\\} \\| \\$ \\q \\( \\\\": ["a {b} | $ \\q \\( \\"],
    "{a\\|b|c}": ["a|b", "c"],
    # AC-04, user decision: `\}` escapes the closer, so the variant is unclosed.
    "{a|b\\}": ParseException,
    "{a\\}": ParseException,
    # AC-05/06: a lone or whitespace-edged wildcard wrapper is literal.
    "a __ b": ["a __ b"],
    "snake__case text": ["snake__case text"],
    "<lora:foo__bar:1> __a__": ["<lora:foo__bar:1> a-val"],
    "<lora:foo__bar:1>, __a__ x__b__y": ["<lora:foo__bar:1>, a-val xb-valy"],
    "x__y(z) __a__": ["x__y(z) a-val"],
    "x **a** <lora:foo**bar:1> **b**": ["x a-val <lora:foo**bar:1> b-val"],
    "x ** y": ["x ** y"],
    # AC-07: malformed wildcard arguments raise.
    "x __a(v=)__": ParseException,
    "x __a(v=1,,)__": ParseException,
}

CORPUS: list[tuple[str, ParserConfig, Expected]] = [
    (prompt, DEFAULT, expected) for prompt, expected in MAIN_OUTPUTS.items()
] + MAIN_OUTPUTS_WITH_CONFIG


def _generate(prompt: str, config: ParserConfig) -> list[str]:
    generator = CombinatorialPromptGenerator(
        WildcardManager(path=WILDCARDS),
        parser_config=config,
    )
    return [str(p) for p in generator.generate(prompt, MAX_PROMPTS)]


def _check(prompt: str, config: ParserConfig, expected: Expected) -> None:
    if isinstance(expected, list):
        assert _generate(prompt, config) == expected
    else:
        with pytest.raises(expected):
            _generate(prompt, config)


@pytest.mark.parametrize(("prompt", "config", "main_output"), CORPUS)
def test_corpus_matches_main_except_intended_differences(
    prompt: str,
    config: ParserConfig,
    main_output: Expected,
):
    _check(prompt, config, INTENDED_DIFFERENCES.get(prompt, main_output))


def test_every_intended_difference_is_in_the_corpus():
    corpus_prompts = {prompt for prompt, _, _ in CORPUS}
    assert set(INTENDED_DIFFERENCES) <= corpus_prompts


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        # Dynamic wildcard paths after text.
        ("x __${n:a}__", ["x a-val"]),
        ("${n=a} x __${n}__", [" x a-val"]),
        ("x __{a|b}__", ["x a-val"]),
        ("{a|x __${n:b}__}", ["a", "x b-val"]),
        # A trailing backslash stays literal.
        ("a\\", ["a\\"]),
        # Backslashes in wildcard paths are kept, as on main.
        ("__a\\b__", ["__a\\b__"]),
        ("x __a\\b__", ["x __a\\b__"]),
    ],
)
def test_former_regressions(prompt: str, expected: list[str]):
    assert _generate(prompt, DEFAULT) == expected


def test_former_regression_custom_variable_delimiters_raise():
    with pytest.raises(ParseException):
        parse("x <<name>z>>", parser_config=ANGLE_VARIABLES)


def test_former_regression_wildcard_path_keeps_backslash():
    assert parse("__a\\b__") == WildcardCommand("a\\b")
    assert parse("x __a\\b__") == SequenceCommand.from_literals(
        [LiteralCommand("x "), WildcardCommand("a\\b")],
    )


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("$tephanie $0 $10 50% 100% FREE", ["$tephanie $0 $10 50% 100% FREE"]),
        ("{$tephanie|50%|100% FREE}", ["$tephanie", "50%", "100% FREE"]),
        ("x ${n:v} %{a$$b}", ["x v ab"]),
        ("{x ${n:v}|%{a$$b}}", ["x v", "ab"]),
        (
            "__literals__",
            [
                "$tephanie 50% 100% FREE $0 v ab",
                "$tephanie 50% 100% FREE $10 v ab",
            ],
        ),
    ],
)
def test_ac03_literal_dollars_and_percents(prompt: str, expected: list[str]):
    assert _generate(prompt, DEFAULT) == expected


@pytest.mark.parametrize(
    ("prompt", "config"),
    [
        ("x ${n", DEFAULT),
        ("x ${n>z}", DEFAULT),
        ("x ${n=", DEFAULT),
        ("x %{a", DEFAULT),
        ("x %{a}", DEFAULT),
        ("x __a(v=)__", DEFAULT),
        ("x __a(v=1,,)__", DEFAULT),
        ("x __a()__", DEFAULT),
        ("x **a(v=)**", STAR_WILDCARDS),
        ("x <<name>z>>", ANGLE_VARIABLES),
    ],
)
def test_ac05_complete_opener_with_malformed_body_raises(
    prompt: str,
    config: ParserConfig,
):
    with pytest.raises(ParseException):
        parse(prompt, parser_config=config)


@pytest.mark.parametrize(
    ("prompt", "config"),
    [
        ("a __ b", DEFAULT),
        ("snake__case text", DEFAULT),
        ("__unmatched", DEFAULT),
        # Unbalanced parentheses never commit to arguments.
        ("__foo(animal=(bear)__", DEFAULT),
        ("x ** y", STAR_WILDCARDS),
        ("**unmatched", STAR_WILDCARDS),
    ],
)
def test_ac05_incomplete_command_lookalikes_are_literal(
    prompt: str,
    config: ParserConfig,
):
    assert parse(prompt, parser_config=config) == LiteralCommand(prompt)


def test_ac05_custom_variable_access_still_parses():
    assert parse("x <<name>> y", parser_config=ANGLE_VARIABLES) == (
        SequenceCommand.from_literals(
            [
                LiteralCommand("x "),
                VariableAccessCommand("name"),
                LiteralCommand(" y"),
            ],
        )
    )


@pytest.mark.parametrize(
    ("prompt", "config", "expected"),
    [
        ("<lora:foo__bar:1> __a__", DEFAULT, ["<lora:foo__bar:1> a-val"]),
        (
            "<lora:foo__bar:1>, __a__ x__b__y",
            DEFAULT,
            ["<lora:foo__bar:1>, a-val xb-valy"],
        ),
        ("x__y(z) __a__", DEFAULT, ["x__y(z) a-val"]),
        (
            "x **a** <lora:foo**bar:1> **b**",
            STAR_WILDCARDS,
            ["x a-val <lora:foo**bar:1> b-val"],
        ),
    ],
)
def test_ac06_lora_tags_and_wildcards(
    prompt: str,
    config: ParserConfig,
    expected: list[str],
):
    assert _generate(prompt, config) == expected


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        # Top level.
        ("a \\{b\\} \\| \\$ \\q \\( \\\\", ["a {b} | $ \\q \\( \\"]),
        ("a\\\\", ["a\\"]),
        ("\\__a__", ["__a__"]),
        # In variants.
        ("{a\\|b|c}", ["a|b", "c"]),
        ("{\\{|\\}}", ["{", "}"]),
        ("{a\\\\}", ["a\\"]),
        # In wildcard values, decoded once when the generator reparses them.
        ("__escaped__", ["v {x} d 50%"]),
        # Escape once inside a variable value.
        ("${q=\\{lit\\}}${q}", ["{lit}"]),
    ],
)
def test_ac04_escapes(prompt: str, expected: list[str]):
    assert _generate(prompt, DEFAULT) == expected


@pytest.mark.parametrize("prompt", ["{a\\}", "{a|b\\}"])
def test_ac04_escaped_variant_closer_leaves_variant_unclosed(prompt: str):
    with pytest.raises(ParseException):
        parse(prompt)


def test_ac04_escape_in_wildcard_path():
    assert parse("__x\\_y__") == WildcardCommand("x_y")


@pytest.mark.parametrize("prompt", ["a\\", "a\\q", "\\(word\\)", "x\\//abc"])
def test_ac04_backslash_that_starts_no_escape_is_kept(prompt: str):
    assert parse(prompt) == LiteralCommand(prompt)


def test_ac04_kept_backslash_in_variant_does_not_start_comment():
    assert _generate("{x\\//abc|z}", DEFAULT) == ["x\\//abc", "z"]


def test_wildcard_path_is_plain_string_after_literal_merge():
    command = parse("x __c/red__")
    assert command == SequenceCommand.from_literals(
        [LiteralCommand("x "), WildcardCommand("c/red")],
    )


def test_wildcard_argument_value_keeps_escaped_newline():
    command = parse("__echo(x=one\\\ntwo)__")
    assert isinstance(command, WildcardCommand)
    assert command.variables["x"] == LiteralCommand("one\\\ntwo")


def test_wildcard_argument_escapes_of_configured_delimiters_stay_literal():
    config = ParserConfig(variant_start="((", variant_end="))")
    command = parse("__echo(x=\\(\\(a\\)\\))__", parser_config=config)
    assert isinstance(command, WildcardCommand)
    assert command.variables["x"] == LiteralCommand("((a))")
