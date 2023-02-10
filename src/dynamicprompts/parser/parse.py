from __future__ import annotations

import warnings
from typing import cast

import pyparsing as pp

from dynamicprompts.commands import (
    Command,
    LiteralCommand,
    SequenceCommand,
    VariantCommand,
    VariantOption,
    WildcardCommand,
)
from dynamicprompts.parser.action_builder import ActionBuilder

real_num1 = pp.Combine(pp.Word(pp.nums) + "." + pp.Word(pp.nums))
real_num2 = pp.Combine(pp.Word(pp.nums) + ".")
real_num3 = pp.Combine("." + pp.Word(pp.nums))
real_num4 = pp.Word(pp.nums)

real_num = real_num1 | real_num2 | real_num3 | real_num4
double_underscore = "__"
wildcard_enclosure = pp.Suppress(double_underscore)
default_braces = (pp.Suppress("{"), pp.Suppress("}"))


class Parser:
    def __init__(self, builder: ActionBuilder):
        warnings.warn(
            f"{self.__class__.__qualname__} is deprecated and will be removed in a future version. "
            "Instead, directly call `parse(prompt)`.",
            DeprecationWarning,
        )
        self._builder = builder
        self._prompt = create_parser()

    @property
    def prompt(self):
        return self._prompt

    def parse(self, prompt: str) -> SequenceCommand:
        tokens = self.prompt.parse_string(prompt, parse_all=True)
        return cast(SequenceCommand, tokens[0])


def _configure_range() -> pp.ParserElement:
    hyphen = pp.Suppress("-")
    variant_delim = pp.Suppress("$$")

    # Exclude:
    # - $, which is used to indicate the end of the separator definition i.e. {1$$ and $$X|Y|Z}
    # - }, which is used to indicate the end of a variant
    # Allowed:
    # - | is allowed as a separator
    separator = pp.Word(pp.printables + " ", exclude_chars="$}")(
        "separator",
    ).leave_whitespace()

    bound = pp.common.integer
    bound_range1 = bound("exact")
    bound_range2 = bound("lower") + hyphen
    bound_range3 = hyphen + bound("upper")
    bound_range4 = bound("lower") + hyphen + bound("upper")

    bound_range = pp.Group(
        bound_range4 | bound_range3 | bound_range2 | bound_range1,
    )
    bound_expr = pp.Group(
        bound_range("range")
        + variant_delim
        + pp.Opt(separator + variant_delim, default=",")("separator"),
    )

    return bound_expr


def _configure_wildcard() -> pp.ParserElement:
    wildcard = wildcard_enclosure + ... + wildcard_enclosure

    return wildcard("wildcard").leave_whitespace()


def _configure_literal_sequence(
    braces: tuple[pp.Suppress, pp.Suppress],
    is_variant_literal: bool = False,
) -> pp.ParserElement:
    # Characters that are not allowed in a literal
    # - { denotes the start of a variant
    # - # denotes the start of a comment
    left_brace, right_brace = braces
    non_literal_chars = rf"#{left_brace.expr}"

    if is_variant_literal:
        # Inside a variant the following characters are also not allowed
        # - } denotes the end of a variant
        # - | denotes the end of a variant option
        # - $ denotes the end of a bound expression
        non_literal_chars += rf"|${right_brace.expr}"

    literal = pp.Regex(rf"((?!{double_underscore})[^{non_literal_chars}])+")(
        "literal",
    ).leave_whitespace()
    literal_sequence = pp.OneOrMore(literal)

    return literal_sequence


def _create_weight_parser() -> pp.ParserElement:
    weight_delim = pp.Suppress("::")
    weight = (pp.common.real | pp.common.integer) + weight_delim

    return weight


def _configure_variants(
    bound_expr: pp.ParserElement,
    prompt: pp.ParserElement,
    *,
    braces: tuple[pp.Suppress, pp.Suppress],
) -> pp.ParserElement:
    weight = _create_weight_parser()
    left_brace, right_brace = braces

    variant = pp.Group(pp.Opt(weight, default=1)("weight") + prompt()("val"))
    variants_list = pp.Group(pp.delimited_list(variant, delim="|"))

    variants = (
        left_brace
        + pp.Group(pp.Opt(bound_expr)("bound_expr") + variants_list("variants"))
        + right_brace
    )

    return variants.leave_whitespace()


def _parse_literal_command(parse_result: pp.ParseResults) -> LiteralCommand:
    s = " ".join(parse_result)
    return LiteralCommand(s)


def _parse_sequence_or_single_command(parse_result: pp.ParseResults) -> Command:
    children = list(parse_result)
    assert all(isinstance(c, Command) for c in children)
    if len(children) == 1:  # If there is only one child, return it directly
        return children[0]
    return SequenceCommand(tokens=children)


def _parse_variant_command(parse_result: pp.ParseResults) -> VariantCommand:
    assert len(parse_result) == 1
    parts = parse_result[0].as_dict()
    variants = [
        VariantOption(value=v["val"], weight=float(v["weight"][0]))
        for v in parts["variants"]
    ]
    if "bound_expr" in parts:
        min_bound, max_bound, separator = _parse_bound_expr(
            parts["bound_expr"],
            max_options=len(variants),
        )
    else:
        min_bound = max_bound = 1
        separator = ","
    return VariantCommand(
        variants,
        min_bound=min_bound,
        max_bound=max_bound,
        separator=separator,
    )


def _parse_wildcard_command(parse_result: pp.ParseResults) -> WildcardCommand:
    wildcard = parse_result[0]
    assert isinstance(wildcard, str)
    return WildcardCommand(wildcard=wildcard)


def _parse_bound_expr(expr, max_options):
    lbound = 1
    ubound = max_options
    separator = ","

    expr = expr[0]

    if "range" in expr:
        rng = expr["range"]
        if "exact" in rng:
            lbound = ubound = rng["exact"]
        else:
            if "lower" in expr["range"]:
                lbound = int(expr["range"]["lower"])
            if "upper" in expr["range"]:
                ubound = int(expr["range"]["upper"])

    if "separator" in expr:
        separator = expr["separator"][0]

    return lbound, ubound, separator


def create_parser(
    *,
    braces: tuple[pp.Suppress, pp.Suppress] = default_braces,
) -> pp.ParserElement:
    bound_expr = _configure_range()

    prompt = pp.Forward()
    variant_prompt = pp.Forward()

    wildcard = _configure_wildcard()
    literal_sequence = _configure_literal_sequence(braces=braces)
    variant_literal_sequence = _configure_literal_sequence(
        is_variant_literal=True,
        braces=braces,
    )
    variants = _configure_variants(bound_expr, variant_prompt, braces=braces)

    chunk = variants | wildcard | literal_sequence
    variant_chunk = variants | wildcard | variant_literal_sequence

    prompt <<= pp.ZeroOrMore(chunk)("prompt")
    variant_prompt <<= pp.ZeroOrMore(variant_chunk)("prompt")

    # Configure comments
    prompt.ignore("#" + pp.restOfLine)
    prompt.ignore("//" + pp.restOfLine)
    prompt.ignore(pp.c_style_comment)

    wildcard.set_parse_action(_parse_wildcard_command)
    variants.set_parse_action(_parse_variant_command)
    literal_sequence.set_parse_action(_parse_literal_command)
    variant_literal_sequence.set_parse_action(_parse_literal_command)
    prompt.set_parse_action(_parse_sequence_or_single_command)
    variant_prompt.set_parse_action(_parse_sequence_or_single_command)
    return prompt


def parse(prompt: str, braces="{}") -> Command:
    assert len(braces) == 2
    # left_brace.expr, right_brace.expr = braces

    left_brace = pp.Suppress(braces[0])
    right_brace = pp.Suppress(braces[1])

    """
    Parse a prompt string into a commands.
    :param prompt: The prompt string to parse.
    :return: A command representing the parsed prompt.
    """
    tokens = create_parser(braces=(left_brace, right_brace)).parse_string(
        prompt,
        parse_all=True,
    )
    assert (
        tokens and len(tokens) == 1
    )  # If we have more than one token, the prompt is invalid...
    tok = tokens[0]
    assert isinstance(tok, Command)
    return tok
