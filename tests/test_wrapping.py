import pytest
from dynamicprompts.enums import SamplingMethod
from dynamicprompts.parser.parse import parse
from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.wildcards import WildcardManager

from tests.utils import sample_n


# Methods currently supported by wrap command
@pytest.fixture(
    params=[
        SamplingMethod.COMBINATORIAL,
        SamplingMethod.RANDOM,
    ],
)
def scon(request, wildcard_manager: WildcardManager) -> SamplingContext:
    return SamplingContext(
        default_sampling_method=request.param,
        wildcard_manager=wildcard_manager,
    )


def test_wrap_with_wildcard(scon: SamplingContext):
    cmd = parse("%{__wrappers__$${fox|cow}}")
    assert sample_n(cmd, scon, n=4) == {
        "Art Deco, cow, sleek, geometric forms, art deco style",
        "Art Deco, fox, sleek, geometric forms, art deco style",
        "Pop Art, cow, vivid colors, flat color, 2D, strong lines, Pop Art",
        "Pop Art, fox, vivid colors, flat color, 2D, strong lines, Pop Art",
    }


@pytest.mark.parametrize("placeholder", ["…", "᠁", ".........", "..."])
def test_wrap_with_literal(scon: SamplingContext, placeholder: str):
    cmd = parse("%{happy ... on a meadow$${fox|cow}}".replace("...", placeholder))
    assert sample_n(cmd, scon, n=2) == {
        "happy fox on a meadow",
        "happy cow on a meadow",
    }


def test_bad_wrap_is_prefix(scon: SamplingContext):
    cmd = parse("%{happy $${fox|cow}}")
    assert sample_n(cmd, scon, n=2) == {
        "happy fox",
        "happy cow",
    }


def test_wrap_suffix(scon: SamplingContext):
    cmd = parse("%{... in jail$${fox|cow}}")
    assert sample_n(cmd, scon, n=2) == {
        "fox in jail",
        "cow in jail",
    }


def test_wrap_with_variant(scon):
    cmd = parse("%{ {cool|hot} ...$${fox|cow}}")
    assert sample_n(cmd, scon, n=4) == {
        "cool fox",
        "cool cow",
        "hot fox",
        "hot cow",
    }
