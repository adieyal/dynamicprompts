from dynamicprompts.commands import (
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.sampling_context import SamplingContext


def wildcard_to_variant(
    wildcard: WildcardCommand,
    *,
    context: SamplingContext,
    min_bound=1,
    max_bound=1,
    separator=",",
) -> VariantCommand:
    wm = context.wildcard_manager
    wildcard_values = wm.get_all_values(wildcard.wildcard)
    min_bound = min(min_bound, len(wildcard_values))
    max_bound = min(max_bound, len(wildcard_values))

    wildcard_variant = VariantCommand.from_literals_and_weights(
        wildcard_values,
        min_bound=min_bound,
        max_bound=max_bound,
        separator=separator,
        sampling_method=wildcard.sampling_method,
    )
    return wildcard_variant
