from __future__ import annotations

from dynamicprompts.parser.commands import (
    Command,
    LiteralCommand,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.wildcardmanager import WildcardManager


def parse_bound_expr(expr, max_options):
    lbound = 1
    ubound = max_options
    separator = ","

    if expr is None:
        return lbound, ubound, separator
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


class ActionBuilder:
    def __init__(self, wildcard_manager: WildcardManager, ignore_whitespace=False):
        self._wildcard_manager = wildcard_manager
        self._ignore_whitespace = ignore_whitespace

    def create_literal_command(self, token) -> LiteralCommand:
        return LiteralCommand(token)

    def create_wildcard_command(self, token: str) -> WildcardCommand:
        return WildcardCommand(self._wildcard_manager, token)

    def create_variant_command(self, variants, min_bound=1, max_bound=1, sep=","):
        return VariantCommand(variants, min_bound, max_bound, sep)

    def create_sequence_command(self, token_list: list[Command]):
        return SequenceCommand(token_list)

    def create_generator(self):
        raise NotImplementedError()

    def get_wildcard_action(self, token) -> WildcardCommand:
        return self.create_wildcard_command(token)

    def get_variant_action(self, token):
        parts = token[0].as_dict()
        variants = parts["variants"]
        variants = [{"weight": v["weight"], "val": v["val"]} for v in variants]
        if "bound_expr" in parts:
            min_bound, max_bound, sep = parse_bound_expr(
                parts["bound_expr"],
                max_options=len(variants),
            )
            command = self.create_variant_command(variants, min_bound, max_bound, sep)
        else:
            command = self.create_variant_command(variants)

        return command

    def get_literal_action(self, token) -> LiteralCommand:
        if isinstance(token, str):
            token = [token]
        s = " ".join(token)
        return self.create_literal_command(s)

    def get_sequence_action(self, token_list: list[Command]) -> SequenceCommand:
        return self.create_sequence_command(token_list)
