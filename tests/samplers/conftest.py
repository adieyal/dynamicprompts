import pytest
from dynamicprompts.commands.base import SamplingMethod
from dynamicprompts.samplers.router import ConcreteSamplerRouter
from dynamicprompts.wildcardmanager import WildcardManager


@pytest.fixture
def random_sampler_manager(wildcard_manager: WildcardManager) -> ConcreteSamplerRouter:
    return ConcreteSamplerRouter(
        wildcard_manager=wildcard_manager,
        default_sampling_method=SamplingMethod.RANDOM,
    )


@pytest.fixture
def cyclical_sampler_manager(
    wildcard_manager: WildcardManager,
) -> ConcreteSamplerRouter:
    return ConcreteSamplerRouter(
        wildcard_manager=wildcard_manager,
        default_sampling_method=SamplingMethod.CYCLICAL,
    )


@pytest.fixture
def combinatorial_sampler_manager(
    wildcard_manager: WildcardManager,
) -> ConcreteSamplerRouter:
    return ConcreteSamplerRouter(
        wildcard_manager=wildcard_manager,
        default_sampling_method=SamplingMethod.COMBINATORIAL,
    )
