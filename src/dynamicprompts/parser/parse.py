"""
A parser for a prompt grammar which is roughly as follows:

<prompt> ::= (<chunk>)*
<variant_prompt> ::= (<variant_chunk>)*
<chunk> ::= <variable_assignment> | <variable_access> | <variants> | <wildcard> | <literal_sequence>
<variant_chunk> ::= <variable_access> | <variants> | <wildcard> | <variant_literal_sequence>
<variants> ::= <variant_start> <sampling_method>?(<bound><separator>?)? <variants_list>? <variant_end>
<variants_list> ::= <variant> ("|" <variant>)*
<variant> ::= <weight>? <variant_prompt>
<weight> ::= <real> | <integer>
<variant_start> ::= "{"  # Can be configured to an arbitrary string
<variant_end> ::= "}"    # Can be configured to an arbitrary string
<sampling_method> ::= "!"|"~"|"@"
<bound> :: <integer>(-<integer)?$$
<separator> ::= [^$}]+$$
<wildcard> ::= <wildcard_enclosure> <sampling_method> <path> <wildcard_enclosure>
<wildcard_enclosure> ::= "__" # Can be configured to an arbitrary string
<path>::=  ~"__" + [^{}#]+"
<literal>:=[^#<variant_start>]+
<variant_literal>:=[^#$|<variant_start><variant_end>]+
<literal_sequence> ::= <literal>+
<variant_literal_sequence> ::= <variant_literal>+
<variable_assignment> ::= "${" <variable_name> "=" <variant_chunk> "}"
<variable_access> ::= "${" <variable_name> (":" <variant_chunk>)? "}"

Note that whitespace is preserved in case it is significant to the user.
"""

from __future__ import annotations

import re
from functools import partial
from typing import Iterable
from weakref import WeakKeyDictionary

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
from dynamicprompts.commands.variable_commands import (
    VariableAccessCommand,
    VariableAssignmentCommand,
)
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

OPT_WS = pp.Opt(pp.White())  # Optional whitespace

var_name = pp.Word(pp.alphas + "_-", pp.alphanums + "_-")

sampler_symbol_to_method = {
    "~": SamplingMethod.RANDOM,
    "!": SamplingMethod.COMBINATORIAL,
    "@": SamplingMethod.CYCLICAL,
}


def _configure_range() -> pp.ParserElement:
    hyphen = pp.Suppress("-")
    variant_delim = pp.Suppress("$$")

    # Exclude:
    # - $, which is used to indicate the end of the separator definition i.e. {1$$ and $$X|Y|Z}
    # - }, which is used to indicate the end of a variant
    # Allowed:
    # - | is allowed as a separator
    separator = pp.Word(pp.printables + " ", exclude_chars="${}")(
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
    wildcard_path_re = r"((?!" + re.escape(parser_config.wildcard_wrap) + r")[^({}#])+"
    wildcard_path = pp.Regex(wildcard_path_re)("path").leave_whitespace()
    wildcard_enclosure = pp.Suppress(parser_config.wildcard_wrap)
    wildcard_variable_spec = (
        OPT_WS
        + pp.Suppress("(")
        + pp.Regex(r"[^)]+")("variable_spec")
        + pp.Suppress(")")
    )

    wildcard = (
        wildcard_enclosure
        + pp.Opt(sampler_symbol)("sampling_method")
        + wildcard_path
        + pp.Opt(wildcard_variable_spec)
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
    # - $ denotes the start of a variable command (or whatever variable_start is set to)
    non_literal_chars = rf"#{parser_config.variant_start}{parser_config.variable_start}"

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

    variant = pp.Group(
        OPT_WS + pp.Opt(weight, default=1)("weight") + prompt()("val") + OPT_WS,
    )
    variants_list = pp.Group(pp.delimited_list(variant, delim="|"))

    variants = pp.Group(
        variant_start
        + OPT_WS
        + pp.Opt(sampler_symbol)("sampling_method")
        + pp.Opt(bound_expr)("bound_expr")
        + OPT_WS
        + variants_list("variants")
        + OPT_WS
        + variant_end,
    )

    return variants.leave_whitespace()


def _configure_variable_access(
    parser_config: ParserConfig,
    prompt: pp.ParserElement,
) -> pp.ParserElement:
    variable_access = pp.Group(
        pp.Suppress(parser_config.variable_start)
        + OPT_WS
        + var_name("name")
        + OPT_WS
        + pp.Optional(pp.Literal(":") + OPT_WS + prompt()("default"))
        + OPT_WS
        + pp.Suppress(parser_config.variable_end),
    )
    return variable_access.leave_whitespace()


def _configure_variable_assignment(
    parser_config: ParserConfig,
    prompt: pp.ParserElement,
) -> pp.ParserElement:
    variable_assignment = pp.Group(
        pp.Suppress(parser_config.variable_start)
        + OPT_WS
        + var_name("name")
        + OPT_WS
        + pp.Literal("=")
        + pp.Opt(pp.Literal("!"))("immediate")
        + OPT_WS
        + prompt()("value")
        + OPT_WS
        + pp.Suppress(parser_config.variable_end),
    )
    return variable_assignment.leave_whitespace()


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


def _parse_variable_spec(
    variable_spec: str,
    parser_config: ParserConfig,
) -> Iterable[tuple[str, Command]]:
    """
    Parse a wildcard command's variable spec string to a variable->Command iterable.
    """
    for pair in variable_spec.split(","):
        key, _, value = pair.partition("=")
        value = value.strip()
        command: Command
        if value.isalnum():  # no need to bother...
            command = LiteralCommand(value)
        else:
            command = parse(value, parser_config=parser_config)
        yield key.strip(), command


def _parse_wildcard_command(
    parse_result: pp.ParseResults,
    *,
    parser_config: ParserConfig,
) -> WildcardCommand:
    parts = parse_result.as_dict()
    wildcard = parts.get("path")

    sampling_method_symbol = parts.get("sampling_method")
    sampling_method = _parse_sampling_method(sampling_method_symbol)

    variable_spec = parts.get("variable_spec")
    if variable_spec:
        variables = dict(
            _parse_variable_spec(variable_spec, parser_config=parser_config),
        )
    else:
        variables = {}

    assert isinstance(wildcard, str)
    return WildcardCommand(
        wildcard=wildcard,
        sampling_method=sampling_method,
        variables=variables,
    )


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


def _parse_variable_access_command(
    parse_result: pp.ParseResults,
) -> VariableAccessCommand:
    parts = parse_result[0].as_dict()
    return VariableAccessCommand(name=parts["name"], default=parts.get("default"))


def _parse_variable_assignment_command(
    parse_result: pp.ParseResults,
) -> VariableAssignmentCommand:
    parts = parse_result[0].as_dict()
    return VariableAssignmentCommand(
        name=parts["name"],
        value=parts["value"],
        immediate=("immediate" in parts),
    )


def create_parser(
    *,
    parser_config: ParserConfig,
) -> pp.ParserElement:
    bound_expr = _configure_range()

    prompt = pp.Forward()
    variant_prompt = pp.Forward()

    variable_access = _configure_variable_access(
        parser_config=parser_config,
        prompt=variant_prompt,
    )
    variable_assignment = _configure_variable_assignment(
        parser_config=parser_config,
        prompt=variant_prompt,
    )
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

    chunk = (
        variable_assignment | variable_access | variants | wildcard | literal_sequence
    )
    variant_chunk = variable_access | variants | wildcard | variant_literal_sequence

    prompt <<= pp.ZeroOrMore(chunk)("prompt")
    variant_prompt <<= pp.ZeroOrMore(variant_chunk)("prompt")

    # Configure comments
    prompt.ignore("#" + pp.restOfLine)
    prompt.ignore("//" + pp.restOfLine)
    prompt.ignore(pp.c_style_comment)

    wildcard.set_parse_action(
        partial(_parse_wildcard_command, parser_config=parser_config),
    )
    variants.set_parse_action(_parse_variant_command)
    literal_sequence.set_parse_action(_parse_literal_command)
    variant_literal_sequence.set_parse_action(_parse_literal_command)
    variable_access.set_parse_action(_parse_variable_access_command)
    variable_assignment.set_parse_action(_parse_variable_assignment_command)
    prompt.set_parse_action(_parse_sequence_or_single_command)
    variant_prompt.set_parse_action(_parse_sequence_or_single_command)
    return prompt


# Cache of parsers, keyed by parser config. Since parser configs are immutable,
# we can use them as keys; we still use a weak key dictionary to avoid leaking
# memory if a custom parser config is garbage collected.
_parser_cache: WeakKeyDictionary[ParserConfig, pp.ParserElement] = WeakKeyDictionary()


def get_cached_parser(parser_config: ParserConfig):
    """
    Get a cached parser for the given parser config,
    or create one if it doesn't exist.
    """
    try:
        return _parser_cache[parser_config]
    except KeyError:
        parser = create_parser(parser_config=parser_config)
        _parser_cache[parser_config] = parser
        return parser


def parse(
    prompt: str,
    parser_config: ParserConfig = default_parser_config,
) -> Command:
    """
    Parse a prompt string into a commands.
    :param prompt: The prompt string to parse.
    :return: A command representing the parsed prompt.
    """
    if prompt.isalnum():  # no need to actually parse anything
        return LiteralCommand(prompt)

    tokens = get_cached_parser(parser_config).parse_string(
        prompt,
        parse_all=True,
    )
    if len(tokens) != 1:
        raise ValueError(f"Could not parse prompt {prompt!r}")

    tok = tokens[0]
    assert isinstance(tok, Command)
    return tok
