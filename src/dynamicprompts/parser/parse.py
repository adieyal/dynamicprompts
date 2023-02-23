from __future__ import annotations

import re
import warnings
from typing import cast

import pyparsing as pp

from dynamicprompts.commands import (
    Command,
    LiteralCommand,
    SamplingMethod,
    SequenceCommand,
    VariantCommand,
    VariantOption,
    WildcardCommand,
)
from dynamicprompts.parser.action_builder import ActionBuilder
from dynamicprompts.parser.config import ParserConfig, default_parser_config

real_num1 = pp.Combine(pp.Word(pp.nums) + "." + pp.Word(pp.nums))
real_num2 = pp.Combine(pp.Word(pp.nums) + ".")
real_num3 = pp.Combine("." + pp.Word(pp.nums))
real_num4 = pp.Word(pp.nums)

real_num = real_num1 | real_num2 | real_num3 | real_num4
sampler_random = pp.Char("~")
sampler_combinatorial = pp.Char("!")
sampler_cyclical = pp.Char("@")
sampler_symbol = sampler_random | sampler_combinatorial | sampler_cyclical

sampler_symbol_to_method = {
    "~": SamplingMethod.RANDOM,
    "!": SamplingMethod.COMBINATORIAL,
    "@": SamplingMethod.CYCLICAL,
}


class Parser:
    def __init__(self, builder: ActionBuilder):
        warnings.warn(
            f"{self.__class__.__qualname__} is deprecated and will be removed in a future version. "
            "Instead, directly call `parse(prompt)`.",
            DeprecationWarning,
        )

        self._builder = builder
        self._prompt = create_parser(parser_config=default_parser_config)

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


def _configure_wildcard(
    parser_config: ParserConfig,
) -> pp.ParserElement:
    wildcard_path = pp.Regex(
        r"((?!" + re.escape(parser_config.wildcard_wrap) + r")[^{}#])+",
    )("path").leave_whitespace()
    wildcard_enclosure = pp.Suppress(parser_config.wildcard_wrap)
    wildcard = (
        wildcard_enclosure
        + pp.Optional(sampler_symbol)("sampling_method")
        + wildcard_path
        + wildcard_enclosure
    )

    return wildcard("wildcard").leave_whitespace()


def _configure_literal_sequence(
    parser_config: ParserConfig,
    is_variant_literal: bool = False,
) -> pp.ParserElement:
    # Characters that are not allowed in a literal
    # - { denotes the start of a variant (or whatever variant_start is set to  )
    # - # denotes the start of a comment
    non_literal_chars = rf"#{parser_config.variant_start}"

    if is_variant_literal:
        # Inside a variant the following characters are also not allowed
        # - } denotes the end of a variant (or whatever right brace is set to)
        # - | denotes the end of a variant option
        # - $ denotes the end of a bound expression
        non_literal_chars += rf"|${parser_config.variant_end}"

    non_literal_chars = re.escape(non_literal_chars)
    literal = pp.Regex(
        rf"((?!{re.escape(parser_config.wildcard_wrap)})[^{non_literal_chars}])+",
    )(
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
    parser_config: ParserConfig,
) -> pp.ParserElement:
    weight = _create_weight_parser()
    variant_start = pp.Suppress(parser_config.variant_start)
    variant_end = pp.Suppress(parser_config.variant_end)

    variant = pp.Group(pp.Opt(weight, default=1)("weight") + prompt()("val"))
    variants_list = pp.Group(pp.delimited_list(variant, delim="|"))

    variants = pp.Group(
        variant_start
        + pp.Optional(sampler_symbol)("sampling_method")
        + pp.Opt(bound_expr)("bound_expr")
        + variants_list("variants")
        + variant_end,
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

    sampling_method_symbol = parts.get("sampling_method")
    sampling_method = _parse_sampling_method(sampling_method_symbol)

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
        sampling_method=sampling_method,
    )


def _parse_sampling_method(sampling_method_symbol: str | None) -> SamplingMethod | None:
    if sampling_method_symbol is None:
        return None
    try:
        return sampler_symbol_to_method[sampling_method_symbol]
    except KeyError:
        raise ValueError(
            f"Unexpected sampling method: {sampling_method_symbol}.",
        ) from None


def _parse_wildcard_command(parse_result: pp.ParseResults) -> WildcardCommand:
    parts = parse_result.as_dict()
    wildcard = parts.get("path")

    sampling_method_symbol = parts.get("sampling_method")
    sampling_method = _parse_sampling_method(sampling_method_symbol)

    assert isinstance(wildcard, str)
    return WildcardCommand(wildcard=wildcard, sampling_method=sampling_method)


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
    parser_config: ParserConfig,
) -> pp.ParserElement:
    bound_expr = _configure_range()

    prompt = pp.Forward()
    variant_prompt = pp.Forward()

    wildcard = _configure_wildcard(parser_config=parser_config)
    literal_sequence = _configure_literal_sequence(parser_config=parser_config)
    variant_literal_sequence = _configure_literal_sequence(
        is_variant_literal=True,
        parser_config=parser_config,
    )
    variants = _configure_variants(
        bound_expr,
        variant_prompt,
        parser_config=parser_config,
    )

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


def parse(
    prompt: str,
    parser_config: ParserConfig = default_parser_config,
) -> Command:
    """
    Parse a prompt string into a commands.
    :param prompt: The prompt string to parse.
    :return: A command representing the parsed prompt.
    """

    tokens = create_parser(parser_config=parser_config).parse_string(
        prompt,
        parse_all=True,
    )
    assert (
        tokens and len(tokens) == 1
    )  # If we have more than one token, the prompt is invalid...
    tok = tokens[0]

    assert isinstance(tok, Command)
    return tok
