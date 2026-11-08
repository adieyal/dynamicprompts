"""
Count the prompts the combinatorial sampler yields for a template, and produce
the prompt at a given index, without enumerating them.
"""

from __future__ import annotations

import dataclasses
import math
from random import Random
from typing import Callable, Union

from dynamicprompts.commands import (
    Command,
    LiteralCommand,
    SamplingMethod,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
    WrapCommand,
)
from dynamicprompts.commands.variable_commands import (
    VariableAccessCommand,
    VariableAssignmentCommand,
)
from dynamicprompts.commands.variant_command import resolve_max_bound
from dynamicprompts.parser.parse import parse
from dynamicprompts.samplers.base import (
    _is_sampled_immediate_assignment,
    resolve_variable,
)
from dynamicprompts.samplers.utils import (
    get_wildcard_not_found_fallback,
    sole_wildcard,
    wildcard_to_variant,
)
from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.sampling_result import SamplingResult

UNBOUNDED_MESSAGE = (
    "The template contains a recursive wildcard (a wildcard that includes itself), "
    "so its number of combinations is unbounded"
)


@dataclasses.dataclass(frozen=True)
class ExactCount:
    value: int  # prompts the combinatorial sampler yields
    has_random_parts: bool  # a random/cyclic part was counted as 1; its text varies


@dataclasses.dataclass(frozen=True)
class UnboundedCount:
    """A recursive wildcard: the combinatorial sampler never ends normally."""


CombinationCount = Union[ExactCount, UnboundedCount]


def count_combinations(command: Command, context: SamplingContext) -> CombinationCount:
    """
    The number of prompts the combinatorial sampler yields for `command`.
    Assumes `context` defaults to combinatorial sampling.
    A random or cyclical part counts as 1. Does not draw from `context.rand`.
    """
    return _count(command, _isolated(context), frozenset())


def combination_at(command: Command, context: SamplingContext, index: int) -> str:
    """
    The prompt the combinatorial sampler yields at `index` for `command`,
    decoded through the counts instead of enumerated.
    Assumes `context` defaults to combinatorial sampling.
    Cyclical parts take the value the sampler gives them at `index`;
    random parts are drawn from `context.rand`.
    Known limit: inside a cyclic wildcard (`__@w__` / cyclic part) whose lines contain an
    immediate assignment sampled from a variant (e.g. `${v=!{a|b|c}} ${v}-{x|y}`),
    this returns the cycle's first value and may differ from `generate()`.
    """
    count = count_combinations(command, context)
    if isinstance(count, UnboundedCount):
        raise ValueError(
            "A template with a recursive wildcard has no prompt at an index",
        )
    if not 0 <= index < count.value:
        raise IndexError(
            f"Prompt index {index} is out of range for {count.value} combinations",
        )
    return str(_sampled_at(command, context, index))


def _isolated(context: SamplingContext) -> SamplingContext:
    # Name and variable resolution may sample random parts; keep that off the live RNG,
    # and make it give the same answer every time it is asked.
    return dataclasses.replace(context, rand=Random(0))


def _wildcard_path(command: WildcardCommand, context: SamplingContext) -> str:
    # The sampler uses the first sample of the (possibly dynamic) name.
    return next(iter(_isolated(context).sample_prompts(command.wildcard, 1))).text


def _wildcard_variant(
    command: VariantCommand,
    wildcard: WildcardCommand,
    context: SamplingContext,
) -> VariantCommand:
    return wildcard_to_variant(
        wildcard,
        context=_isolated(context),
        min_bound=command.min_bound,
        max_bound=command.max_bound,
        separator=command.separator,
    )


def _combined(
    counts: list[CombinationCount],
    combine: Callable[[list[int]], int],
) -> CombinationCount:
    # Unbounded if any part is; otherwise `combine` of the parts' values.
    exact = [c for c in counts if isinstance(c, ExactCount)]
    if len(exact) != len(counts):
        return UnboundedCount()
    return ExactCount(
        combine([c.value for c in exact]),
        any(c.has_random_parts for c in exact),
    )


def _ordered_selections(sizes: list[int], k: int) -> int:
    """
    Ordered k-tuples of distinct positions, each weighted by the product of its
    positions' sizes: k! * e_k(sizes), e_k the elementary symmetric polynomial.
    """
    e = [1] + [0] * k
    for size in sizes:
        for j in range(k, 0, -1):
            e[j] += e[j - 1] * size
    return math.factorial(k) * e[k]


def _count(
    command: Command,
    context: SamplingContext,
    expanding: frozenset[str],
) -> CombinationCount:
    # Same branch order as Sampler.generator_from_command.
    if context.yields_once(command):
        return ExactCount(1, True)
    if isinstance(command, LiteralCommand):
        return ExactCount(1, False)
    if isinstance(command, SequenceCommand):
        tokens, context = context.process_variable_assignments(command.tokens)
        return _combined([_count(t, context, expanding) for t in tokens], math.prod)
    if isinstance(command, VariantCommand):
        return _count_variant(command, context, expanding)
    if isinstance(command, WildcardCommand):
        return _count_wildcard(command, context, expanding)
    if isinstance(command, VariableAssignmentCommand):
        raise NotImplementedError("VariableAssignmentCommand should never be sampled")
    if isinstance(command, VariableAccessCommand):
        value = resolve_variable(command, context)
        return _count(value, context.for_sampling_variable(command.name), expanding)
    if isinstance(command, WrapCommand):
        return _combined(
            [
                _count_sampled(command.wrapper, context, expanding),
                _count_sampled(command.inner, context, expanding),
            ],
            math.prod,
        )
    raise NotImplementedError(f"Cannot count {command.__class__.__name__}")


def _count_sampled(
    prompt: str | Command,
    context: SamplingContext,
    expanding: frozenset[str],
) -> CombinationCount:
    # Mirrors SamplingContext.sample_prompts.
    if not prompt:
        return ExactCount(0, False)
    if isinstance(prompt, str):
        prompt = parse(prompt, parser_config=context.parser_config)
    return _count(prompt, context, expanding)


def _count_variant(
    command: VariantCommand,
    context: SamplingContext,
    expanding: frozenset[str],
) -> CombinationCount:
    if len(command.variants) == 0:
        return ExactCount(0, False)
    wildcard = sole_wildcard(command)
    if wildcard is not None:
        variant = _wildcard_variant(command, wildcard, context)
        if not variant.variants:
            return _count_wildcard(wildcard, context, expanding)
        path = _wildcard_path(wildcard, context)
        if path in expanding:
            return UnboundedCount()
        return _count_variant(variant, context, expanding | {path})
    command = command.adjust_range()
    bounds = range(
        command.min_bound,
        resolve_max_bound(command.max_bound, len(command)) + 1,
    )
    return _combined(
        [_count(v, context, expanding) for v in command.values],
        lambda sizes: sum(_ordered_selections(sizes, k) for k in bounds),
    )


def _count_wildcard(
    command: WildcardCommand,
    context: SamplingContext,
    expanding: frozenset[str],
) -> CombinationCount:
    path = _wildcard_path(command, context)
    if path in expanding:
        return UnboundedCount()
    context = context.with_variables(command.variables)
    values = context.wildcard_manager.get_values(path)
    if not values:
        return ExactCount(1, False)  # the not-found text, once
    expanding = expanding | {path}
    return _combined(
        [
            _count_sampled(line, context, expanding)
            for line in values.iterate_string_values_weighted()
        ],
        sum,
    )


def _exact(count: CombinationCount) -> int:
    if isinstance(count, UnboundedCount):
        raise ValueError(UNBOUNDED_MESSAGE)
    return count.value


def _mixed_radix(index: int, sizes: list[int]) -> list[int]:
    # The last position varies fastest, as in the sampler's nested loops.
    digits = []
    for size in reversed(sizes):
        index, digit = divmod(index, size)
        digits.append(digit)
    return digits[::-1]


def _selection_at(sizes: list[int], k: int, index: int) -> tuple[list[int], int]:
    """
    The k-tuple of positions holding `index`, in the order of
    VariantCommand.get_value_combinations, and the index within that tuple.
    """
    positions: list[int] = []
    remaining = list(range(len(sizes)))
    weight = 1
    for depth in range(k):
        for p in remaining:
            rest = [sizes[q] for q in remaining if q != p]
            block = weight * sizes[p] * _ordered_selections(rest, k - depth - 1)
            if index < block:
                positions.append(p)
                remaining.remove(p)
                weight *= sizes[p]
                break
            index -= block
    return positions, index


def _sampled_at(
    prompt: str | Command,
    context: SamplingContext,
    index: int,
) -> SamplingResult:
    # Mirrors SamplingContext.sample_prompts.
    if isinstance(prompt, str):
        prompt = parse(prompt, parser_config=context.parser_config)
    result = _at(prompt, context, index)
    return result.whitespace_squashed() if context.ignore_whitespace else result


def _at(command: Command, context: SamplingContext, index: int) -> SamplingResult:
    # `index` is the output's position in a fresh generator for `command`; for a
    # random or cyclical part, the number of values drawn from it before this one.
    if context.yields_once(command):
        return _nonfinite_at(command, context, index)
    if isinstance(command, LiteralCommand):
        return SamplingResult(text=command.literal)
    if isinstance(command, SequenceCommand):
        tokens, context = context.process_variable_assignments(command.tokens)
        sizes = [_exact(count_combinations(t, context)) for t in tokens]
        parts = [
            _at(
                t,
                context,
                _token_draw(tokens, p, index) if context.yields_once(t) else d,
            )
            for p, (t, d) in enumerate(zip(tokens, _mixed_radix(index, sizes)))
        ]
        # The sampler joins the tokens between two empty sentinels.
        return SamplingResult.joined(
            [SamplingResult(text=""), *parts, SamplingResult(text="")],
            separator=command.separator,
        )
    if isinstance(command, VariantCommand):
        return _variant_at(command, context, index)
    if isinstance(command, WildcardCommand):
        return _wildcard_at(command, context, index)
    if isinstance(command, VariableAssignmentCommand):
        raise NotImplementedError("VariableAssignmentCommand should never be sampled")
    if isinstance(command, VariableAccessCommand):
        value = resolve_variable(command, context)
        return _at(value, context.for_sampling_variable(command.name), index)
    if isinstance(command, WrapCommand):
        inner_size = _exact(
            _count_sampled(command.inner, _isolated(context), frozenset()),
        )
        wrapper_index, inner_index = divmod(index, inner_size)
        wrapper = _sampled_at(command.wrapper, context, wrapper_index)
        return wrapper.as_wrapper()(_sampled_at(command.inner, context, inner_index))
    raise NotImplementedError(f"Cannot index {command.__class__.__name__}")


def _token_draw(tokens: list[Command], position: int, row: int) -> int:
    """
    The draw of the random/cyclical token at `position` in a sequence's `row`.
    The sampler keeps one generator per such token for the whole sequence
    (CommandCollection), shared by equal tokens, and draws once per token per row,
    the last token first.
    """
    equal = [p for p, t in enumerate(tokens) if t == tokens[position]]
    return row * len(equal) + sum(p > position for p in equal)


def _combination_at(
    command: VariantCommand,
    sizes: list[int],
    index: int,
) -> tuple[list[int], int]:
    """The positions of the combination holding `index`, and the index within it."""
    for k in range(
        command.min_bound,
        resolve_max_bound(command.max_bound, len(command)) + 1,
    ):
        block = _ordered_selections(sizes, k)
        if index < block:
            return _selection_at(sizes, k, index)
        index -= block
    raise IndexError(f"Prompt index is out of range for {command}")


def _variant_at(
    command: VariantCommand,
    context: SamplingContext,
    index: int,
) -> SamplingResult:
    wildcard = sole_wildcard(command)
    if wildcard is not None:
        variant = _wildcard_variant(command, wildcard, context)
        if not variant.variants:
            return _wildcard_at(wildcard, context, index)
        return _variant_at(variant, context, index)
    command = command.adjust_range()
    sizes = [_exact(count_combinations(v, context)) for v in command.values]
    positions, index = _combination_at(command, sizes, index)
    option_sizes = [sizes[p] for p in positions]
    parts = []
    for m, (p, digit) in enumerate(zip(positions, _mixed_radix(index, option_sizes))):
        value = command.values[p]
        if context.yields_once(value):
            # _combo_to_prompt restarts its generator for each value of the options
            # before it and draws once per value of the options after it.
            digit = index % math.prod(option_sizes[m + 1 :])
        parts.append(_at(value, context, digit))
    return SamplingResult.joined(parts, separator=command.separator)


def _wildcard_at(
    command: WildcardCommand,
    context: SamplingContext,
    index: int,
) -> SamplingResult:
    path = _wildcard_path(command, context)
    context = context.with_variables(command.variables)
    values = context.wildcard_manager.get_values(path)
    if not values:
        return next(get_wildcard_not_found_fallback(command, _isolated(context)))
    for line in values.iterate_string_values_weighted():
        size = _exact(_count_sampled(line, _isolated(context), frozenset()))
        if index < size:
            return _sampled_at(line, context, index)
        index -= size
    raise IndexError(f"Prompt index is out of range for wildcard {path!r}")


def _nonfinite_at(
    command: Command,
    context: SamplingContext,
    draw: int,
) -> SamplingResult:
    """
    The value at `draw` of a fresh generator for a random or cyclical `command`,
    mirroring CyclicalSampler. Random parts are drawn from `context.rand`.
    """
    sampler, context = context.get_sampler_and_context(command)
    if context.default_sampling_method == SamplingMethod.CYCLICAL:
        if isinstance(command, LiteralCommand):
            return SamplingResult(text=command.literal)
        if isinstance(command, SequenceCommand) and not any(
            _is_sampled_immediate_assignment(t) for t in command.tokens
        ):
            # Each token's generator advances once per value.
            tokens, context = context.process_variable_assignments(command.tokens)
            return SamplingResult.joined(
                [_nonfinite_at(t, context, draw) for t in tokens],
                separator=command.separator,
            )
        if isinstance(command, VariantCommand) and command.values:
            return _cyclical_variant_at(command, context, draw)
        if isinstance(command, WildcardCommand):
            return _cyclical_wildcard_at(command, context, draw)
        if isinstance(command, VariableAccessCommand):
            value = resolve_variable(command, context)
            context = context.for_sampling_variable(command.name)
            return _nonfinite_at(value, context, draw)
    # Random parts; and, as an unmatched approximation, a cyclical sequence with a
    # sampled immediate assignment, whose generators are keyed by earlier values.
    return next(iter(sampler.generator_from_command(command, context)))


def _cyclical_variant_at(
    command: VariantCommand,
    context: SamplingContext,
    draw: int,
) -> SamplingResult:
    # The sampler cycles through the combinations, advancing each one's generators.
    wildcard = sole_wildcard(command)
    if wildcard is not None:
        variant = _wildcard_variant(command, wildcard, context)
        return _nonfinite_at(variant, context, draw)
    command = command.adjust_range()
    ones = [1] * len(command.values)
    combinations = sum(
        _ordered_selections(ones, k)
        for k in range(
            command.min_bound,
            resolve_max_bound(command.max_bound, len(command)) + 1,
        )
    )
    draw, combination = divmod(draw, combinations)
    positions, _ = _combination_at(command, ones, combination)
    return SamplingResult.joined(
        [_nonfinite_at(command.values[p], context, draw) for p in positions],
        separator=command.separator,
    )


def _cyclical_wildcard_at(
    command: WildcardCommand,
    context: SamplingContext,
    draw: int,
) -> SamplingResult:
    # The sampler cycles through the lines, advancing each line's generator.
    path = _wildcard_path(command, context)
    context = context.with_variables(command.variables)
    values = context.wildcard_manager.get_values(path)
    if not values:
        return next(get_wildcard_not_found_fallback(command, _isolated(context)))
    lines = list(values.iterate_string_values_weighted())
    draw, line = divmod(draw, len(lines))
    command = parse(lines[line], parser_config=context.parser_config)
    result = _nonfinite_at(command, context, draw)
    return result.whitespace_squashed() if context.ignore_whitespace else result
