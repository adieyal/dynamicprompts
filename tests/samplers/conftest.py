import pytest
from dynamicprompts.commands.base import SamplingMethod
from dynamicprompts.samplers.sampler_manager import ConcreteSamplerManager
from dynamicprompts.wildcardmanager import WildcardManager


@pytest.fixture
def random_sampler_manager(wildcard_manager: WildcardManager) -> ConcreteSamplerManager:
    return ConcreteSamplerManager(
        wildcard_manager=wildcard_manager,
        default_sampling_method=SamplingMethod.RANDOM,
    )


@pytest.fixture
def cyclical_sampler_manager(
    wildcard_manager: WildcardManager,
) -> ConcreteSamplerManager:
    return ConcreteSamplerManager(
        wildcard_manager=wildcard_manager,
        default_sampling_method=SamplingMethod.CYCLICAL,
    )


@pytest.fixture
def combinatorial_sampler_manager(
    wildcard_manager: WildcardManager,
) -> ConcreteSamplerManager:
    return ConcreteSamplerManager(
        wildcard_manager=wildcard_manager,
        default_sampling_method=SamplingMethod.COMBINATORIAL,
    )
