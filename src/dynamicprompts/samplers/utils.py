from __future__ import annotations

import logging
from functools import partial

import pyparsing as pp

from dynamicprompts.commands import (
    LiteralCommand,
    VariantCommand,
    VariantOption,
    WildcardCommand,
)
from dynamicprompts.parser.parse import (
    _configure_variable_access,
    _configure_wildcard_path,
    parse,
)
from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.sampling_result import SamplingResult
from dynamicprompts.types import ResultGen

logger = logging.getLogger(__name__)


def wildcard_to_variant(
    command: WildcardCommand,
    *,
    context: SamplingContext,
    min_bound=1,
    max_bound=1,
    separator=",",
) -> VariantCommand:
    command = replace_wildcard_variables(command=command, context=context)
    values = context.wildcard_manager.get_values(command.wildcard)
    min_bound = min(min_bound, len(values))
    max_bound = min(max_bound, len(values))

    variant_options = [
        VariantOption(parse(v, parser_config=context.parser_config))
        for v in values.iterate_string_values_weighted()
    ]

    wildcard_variant = VariantCommand(
        variant_options,
        min_bound,
        max_bound,
        separator,
        command.sampling_method,
    )
    return wildcard_variant


def get_wildcard_not_found_fallback(
    command: WildcardCommand,
    context: SamplingContext,
) -> ResultGen:
    """
    Logs a warning, then infinitely yields the wrapped wildcard.
    """
    logger.warning(f"No values found for wildcard {command.wildcard}")
    wrapped_wildcard = context.wildcard_manager.to_wildcard(command.wildcard)
    res = SamplingResult(text=wrapped_wildcard)
    while True:
        yield res


def replace_wildcard_variables(
    command: WildcardCommand,
    *,
    context: SamplingContext,
) -> WildcardCommand:
    if context.parser_config.variable_start not in command.wildcard:
        return command

    prompt = pp.SkipTo(context.parser_config.variable_end)
    variable_access = _configure_variable_access(
        parser_config=context.parser_config,
        prompt=prompt,
    )
    variable_access.set_parse_action(
        partial(_replace_variable, variables=context.variables),
    )
    wildcard = _configure_wildcard_path(
        parser_config=context.parser_config,
        variable_ref=variable_access,
    )

    try:
        wildcard_result = wildcard.parse_string(command.wildcard)
        return command.with_content("".join(wildcard_result))
    except Exception:
        logger.warning("Unable to parse wildcard %r", command.wildcard, exc_info=True)
        return command


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
