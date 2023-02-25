from pathlib import Path

import pytest
from dynamicprompts.commands.base import SamplingMethod
from dynamicprompts.sampler_routers.concrete_sampler_router import ConcreteSamplerRouter
from dynamicprompts.wildcardmanager import WildcardManager

WILDCARD_DATA_DIR = Path(__file__).parent / "test_data" / "wildcards"
assert WILDCARD_DATA_DIR.is_dir()


@pytest.fixture(params=["__", "++", "::"])
def wildcard_manager(request) -> WildcardManager:
    return WildcardManager(path=WILDCARD_DATA_DIR, wildcard_wrap=request.param)


@pytest.fixture
def random_sampler_router(wildcard_manager: WildcardManager) -> ConcreteSamplerRouter:
    return ConcreteSamplerRouter(
        wildcard_manager=wildcard_manager,
        default_sampling_method=SamplingMethod.RANDOM,
    )


@pytest.fixture
def cyclical_sampler_router(
    wildcard_manager: WildcardManager,
) -> ConcreteSamplerRouter:
    return ConcreteSamplerRouter(
        wildcard_manager=wildcard_manager,
        default_sampling_method=SamplingMethod.CYCLICAL,
    )


@pytest.fixture
def combinatorial_sampler_router(
    wildcard_manager: WildcardManager,
) -> ConcreteSamplerRouter:
    return ConcreteSamplerRouter(
        wildcard_manager=wildcard_manager,
        default_sampling_method=SamplingMethod.COMBINATORIAL,
    )
