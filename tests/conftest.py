from pathlib import Path

import pytest
from dynamicprompts.commands.base import SamplingMethod
from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.wildcards import WildcardManager
from pytest_lazyfixture import LazyFixture

WILDCARD_DATA_DIR = Path(__file__).parent / "test_data" / "wildcards"
assert WILDCARD_DATA_DIR.is_dir()


@pytest.fixture(params=["__", "++", "::"])
def wildcard_manager(request) -> WildcardManager:
    return WildcardManager(path=WILDCARD_DATA_DIR, wildcard_wrap=request.param)


@pytest.fixture
def random_sampling_context(wildcard_manager: WildcardManager) -> SamplingContext:
    return SamplingContext(
        wildcard_manager=wildcard_manager,
        default_sampling_method=SamplingMethod.RANDOM,
    )


@pytest.fixture
def cyclical_sampling_context(
    wildcard_manager: WildcardManager,
) -> SamplingContext:
    return SamplingContext(
        wildcard_manager=wildcard_manager,
        default_sampling_method=SamplingMethod.CYCLICAL,
    )


@pytest.fixture
def combinatorial_sampling_context(
    wildcard_manager: WildcardManager,
) -> SamplingContext:
    return SamplingContext(
        wildcard_manager=wildcard_manager,
        default_sampling_method=SamplingMethod.COMBINATORIAL,
    )


sampling_context_fixture_names = [
    "combinatorial_sampling_context",
    "cyclical_sampling_context",
    "random_sampling_context",
]
sampling_context_lazy_fixtures = [
    LazyFixture(name) for name in sampling_context_fixture_names
]
