from dynamicprompts.commands import VariantCommand, VariantOption, WildcardCommand
from dynamicprompts.parser.parse import parse
from dynamicprompts.sampling_context import SamplingContext


def wildcard_to_variant(
    command: WildcardCommand,
    *,
    context: SamplingContext,
    min_bound=1,
    max_bound=1,
    separator=",",
) -> VariantCommand:
    values = context.wildcard_manager.get_all_values(command.wildcard)
    min_bound = min(min_bound, len(values))
    max_bound = min(max_bound, len(values))

    variant_options = [VariantOption(parse(v)) for v in values]

    wildcard_variant = VariantCommand(
        variant_options,
        min_bound,
        max_bound,
        separator,
        command.sampling_method,
    )
    return wildcard_variant
