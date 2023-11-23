from __future__ import annotations

from functools import partial

import pyparsing as pp

from dynamicprompts.commands import LiteralCommand
from dynamicprompts.parser.config import ParserConfig
from dynamicprompts.parser.parse import (
    _configure_variable_access,
    _configure_wildcard_path,
)


def resolve_variable_references(
    subject: str,
    *,
    parser_config: ParserConfig,
    variables: dict,
) -> str:
    """
    Parse `subject` for variable references and resolve them.

    If there are no variable references, returns `subject` unchanged.

    """
    if parser_config.variable_start not in subject:
        return subject
    prompt = pp.SkipTo(parser_config.variable_end)
    variable_access = _configure_variable_access(
        parser_config=parser_config,
        prompt=prompt,
    )
    variable_access.set_parse_action(
        partial(_replace_variable, variables=variables),
    )
    wildcard = _configure_wildcard_path(
        parser_config=parser_config,
        variable_ref=variable_access,
    )
    return "".join(wildcard.parse_string(subject))


def _replace_variable(string, location, token, *, variables: dict):
    if isinstance(token, pp.ParseResults):
        var_parts = token[0].as_dict()
        var_name = var_parts.get("name")
        if var_name:
            var_name = var_name.strip()

        default = var_parts.get("default")
        if default:
            default = default.strip()

    else:
        var_name = token

    variable = None
    if var_name:
        variable = variables.get(var_name)

        if isinstance(variable, LiteralCommand):
            variable = variable.literal
        if variable and not isinstance(variable, str):
            raise NotImplementedError(
                "evaluating complex commands within wildcards is not supported right now",
            )
    return variable or default or var_name
