from __future__ import annotations

from typing import cast
import logging

import pyparsing as pp

from .commands import SequenceCommand
from .action_builder import ActionBuilder

logger = logging.getLogger(__name__)

real_num1 = pp.Combine(pp.Word(pp.nums) + "." + pp.Word(pp.nums))
real_num2 = pp.Combine(pp.Word(pp.nums) + ".")
real_num3 = pp.Combine("." + pp.Word(pp.nums))
real_num4 = pp.Word(pp.nums)

real_num = real_num1 | real_num2 | real_num3 | real_num4
double_underscore = "__"
wildcard_enclosure = pp.Suppress(double_underscore)


class Parser:
    def __init__(self, builder: ActionBuilder):
        self._builder = builder
        prompt = self._configure_parser(self._builder)
        self._prompt = prompt

    @property
    def prompt(self):
        return self._prompt

    def parse(self, prompt: str) -> SequenceCommand:
        tokens = self.prompt.parse_string(prompt, parse_all=True)
        return cast(SequenceCommand, tokens[0])

    def _enable_comments(self, prompt):
        prompt.ignore("#" + pp.restOfLine)
        prompt.ignore("//" + pp.restOfLine)
        prompt.ignore(pp.c_style_comment)

    def _configure_range(self):
        hyphen = pp.Suppress("-")
        variant_delim = pp.Suppress("$$")

        separator = pp.Word(pp.alphanums + " ", exclude_chars="$").leave_whitespace()(
            "separator"
        )
        bound = pp.common.integer
        bound_range1 = bound("exact")
        bound_range2 = bound("lower") + hyphen
        bound_range3 = hyphen + bound("upper")
        bound_range4 = bound("lower") + hyphen + bound("upper")

        bound_range = pp.Group(
            bound_range4 | bound_range3 | bound_range2 | bound_range1
        )
        bound_expr = pp.Group(
            bound_range("range")
            + variant_delim
            + pp.Opt(separator + variant_delim, default=",")("separator")
        )

        return bound_expr

    def _configure_wildcard(self):
        wildcard = wildcard_enclosure + ... + wildcard_enclosure

        return wildcard("wildcard")

    def _configure_literal_sequence(self, is_variant_literal=False):

        if is_variant_literal:
            non_literal_chars = r"{}|$"
        else:
            non_literal_chars = r"{}$"

        literal = pp.Regex(rf"((?!{double_underscore})[^{non_literal_chars}\s])+")(
            "literal"
        )
        literal_sequence = pp.OneOrMore(literal)

        return literal_sequence("literal_sequence")

    def _configure_weight(self):
        weight_delim = pp.Suppress("::")
        weight = (pp.common.real | pp.common.integer) + weight_delim

        return weight

    def _configure_variants(self, bound_expr, prompt):
        weight_delim = pp.Suppress("::")

        left_brace, right_brace = map(pp.Suppress, "{}")
        weight = pp.common.integer + weight_delim

        variant_option = prompt
        variant = pp.Group(pp.Opt(weight, default=1)("weight") + variant_option("val"))
        variants_list = pp.Group(pp.delimited_list(variant, delim="|"))

        variants = (
            left_brace
            + pp.Group(pp.Opt(bound_expr)("bound_expr") + variants_list("variants"))
            + right_brace
        )

        return variants

    def _configure_parser(self, builder: ActionBuilder):
        bound_expr = self._configure_range()

        prompt = pp.Forward()
        variant_prompt = pp.Forward()

        wildcard = self._configure_wildcard()
        literal_sequence = self._configure_literal_sequence()
        variant_literal_sequence = self._configure_literal_sequence(is_variant_literal=True)
        variants = self._configure_variants(bound_expr, variant_prompt)

        chunk = variants | wildcard | literal_sequence
        variant_chunk = variants | wildcard | variant_literal_sequence


        prompt <<= pp.ZeroOrMore(chunk)("prompt")
        variant_prompt <<= pp.ZeroOrMore(variant_chunk)("prompt")

        self._enable_comments(prompt)
        wildcard.set_parse_action(builder.get_wildcard_action)
        variants.set_parse_action(builder.get_variant_action)
        literal_sequence.set_parse_action(builder.get_literal_action)
        variant_literal_sequence.set_parse_action(builder.get_literal_action)

        prompt.set_parse_action(builder.get_sequence_action)
        variant_prompt.set_parse_action(builder.get_sequence_action)

        return prompt
