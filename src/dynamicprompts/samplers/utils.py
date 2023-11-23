from __future__ import annotations

import logging

from dynamicprompts.commands import (
    VariantCommand,
    VariantOption,
    WildcardCommand,
)
from dynamicprompts.parser.parse import (
    parse,
)
from dynamicprompts.parser.utils import resolve_variable_references
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
    try:
        wildcard_result = resolve_variable_references(
            command.wildcard,
            parser_config=context.parser_config,
            variables=context.variables,
        )
        if wildcard_result != command.wildcard:
            return command.with_content(wildcard_result)
    except Exception:
        logger.warning("Unable to parse wildcard %r", command.wildcard, exc_info=True)
    return command
