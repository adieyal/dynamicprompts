from __future__ import annotations

import logging

from dynamicprompts.commands import (
    Command,
    VariantCommand,
    VariantOption,
    WildcardCommand,
)
from dynamicprompts.parser.parse import parse
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
    wildcard = next(iter(context.sample_prompts(command.wildcard, 1))).text
    values = context.wildcard_manager.get_values(wildcard)
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
    if isinstance(command.wildcard, Command):
        wildcard = next(iter(context.sample_prompts(command.wildcard, 1))).text
    else:
        wildcard = str(command.wildcard)
    logger.warning(f"No values found for wildcard {wildcard}")
    wrapped_wildcard = context.wildcard_manager.to_wildcard(wildcard)
    res = SamplingResult(text=wrapped_wildcard)
    while True:
        yield res
