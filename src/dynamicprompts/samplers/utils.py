from __future__ import annotations

import logging

from dynamicprompts.commands import (
    Command,
    VariantCommand,
    VariantOption,
    WildcardCommand,
)
from dynamicprompts.commands.variant_command import resolve_max_bound
from dynamicprompts.parser.parse import try_parse
from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.sampling_result import SamplingResult
from dynamicprompts.types import ResultGen

logger = logging.getLogger(__name__)


def sole_wildcard(command: VariantCommand) -> WildcardCommand | None:
    """The wildcard of a variant whose only option is a wildcard (`{2$$__w__}`)."""
    if len(command.values) == 1 and isinstance(command.values[0], WildcardCommand):
        return command.values[0]
    return None


def wildcard_to_variant(
    command: WildcardCommand,
    *,
    context: SamplingContext,
    min_bound: int = 1,
    max_bound: int | None = 1,
    separator: str = ",",
) -> VariantCommand:
    wildcard = next(iter(context.sample_prompts(command.wildcard, 1))).text
    values = context.wildcard_manager.get_values(wildcard)
    max_options = len(values)
    min_bound = min(min_bound, max_options)
    max_bound = resolve_max_bound(max_bound, max_options)

    variant_options = [
        VariantOption(try_parse(v, parser_config=context.parser_config))
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
    The combinatorial sampler takes one value of it.
    """
    if isinstance(command.wildcard, Command):
        wildcard = next(iter(context.sample_prompts(command.wildcard, 1))).text
    else:
        wildcard = str(command.wildcard)
    logger.warning(f"No values found for wildcard {wildcard!r}")
    wrapped_wildcard = context.wildcard_manager.to_wildcard(wildcard)
    res = SamplingResult(text=wrapped_wildcard)
    while True:
        yield res
