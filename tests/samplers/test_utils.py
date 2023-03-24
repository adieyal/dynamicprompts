import pytest
from dynamicprompts.commands import (
    WildcardCommand,
)
from dynamicprompts.samplers.utils import wildcard_to_variant
from dynamicprompts.sampling_context import SamplingContext
from pytest_lazyfixture import lazy_fixture


@pytest.mark.parametrize(
    ("sampling_context",),
    [
        (lazy_fixture("random_sampling_context"),),
        # (lazy_fixture("cyclical_sampling_context"), "wildcard_colours2"),
        # (lazy_fixture("combinatorial_sampling_context"), "wildcard_colours"),
    ],
)
def test_wildcard_to_variant(sampling_context: SamplingContext):
    wildcard_command = WildcardCommand("colors*")
    variant_command = wildcard_to_variant(
        wildcard_command,
        context=sampling_context,
        min_bound=1,
        max_bound=10,
        separator="-",
    )
    assert variant_command.min_bound == 1
    assert variant_command.max_bound == len(
        sampling_context.wildcard_manager.get_all_values("colors*"),
    )
    assert variant_command.separator == "-"
    assert variant_command.sampling_method == wildcard_command.sampling_method
