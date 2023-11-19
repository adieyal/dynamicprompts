import pytest
from dynamicprompts.commands import (
    WildcardCommand,
)
from dynamicprompts.samplers.utils import (
    wildcard_to_variant, 
    replace_wildcard_variables
)
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
        sampling_context.wildcard_manager.get_values("colors*"),
    )
    assert variant_command.separator == "-"
    assert variant_command.sampling_method == wildcard_command.sampling_method

@pytest.mark.parametrize(
    ("sampling_context","initial_wildcard","expected_wildcard","variables"),
    [
        (lazy_fixture("random_sampling_context"),"colors-${temp: warm}-${ finish }", "colors-warm-finish", {}),
        (lazy_fixture("random_sampling_context"),"colors-${temp: warm}-${ finish: matte }", "colors-warm-matte", {}),
        (lazy_fixture("random_sampling_context"),"colors-${temp: warm}-${ finish: matte }", "colors-cold-matte", {"temp": "cold"}),
        (lazy_fixture("random_sampling_context"),"colors-${temp: warm}-${ finish: matte }", "colors-cold-glossy", {"temp": "cold", "finish": "glossy"}),
    ],
)
def test_replace_wildcard_variables_multi_variable(sampling_context: SamplingContext,
                                                   initial_wildcard: str,
                                                   expected_wildcard: str,
                                                   variables: dict):
    var_sampling_context = sampling_context.with_variables(variables=variables)
    wildcard_command = WildcardCommand(initial_wildcard)    
    updated_command = replace_wildcard_variables(command=wildcard_command, context=var_sampling_context)
    assert isinstance(updated_command, WildcardCommand), "updated command is also a WildcardCommand"
    assert updated_command.wildcard == expected_wildcard
