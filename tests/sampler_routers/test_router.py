import pytest
from dynamicprompts.commands import SamplingMethod
from dynamicprompts.sampler_routers.concrete_sampler_router import ConcreteSamplerRouter
from dynamicprompts.samplers.combinatorial import CombinatorialSampler
from dynamicprompts.samplers.cycle import CyclicalSampler
from dynamicprompts.samplers.random import RandomSampler
from dynamicprompts.wildcardmanager import WildcardManager


@pytest.fixture
def router(wildcard_manager: WildcardManager) -> ConcreteSamplerRouter:
    return ConcreteSamplerRouter(
        wildcard_manager=wildcard_manager,
        default_sampling_method=SamplingMethod.RANDOM,
    )


class TestConcreteSamplerRouter:
    def test_sampling_method(self, router):
        assert isinstance(router._samplers[SamplingMethod.RANDOM], RandomSampler)
        assert isinstance(
            router._samplers[SamplingMethod.COMBINATORIAL],
            CombinatorialSampler,
        )
        assert isinstance(router._samplers[SamplingMethod.CYCLICAL], CyclicalSampler)
        assert isinstance(router._samplers[SamplingMethod.DEFAULT], RandomSampler)

        router.default_sampling_method = SamplingMethod.COMBINATORIAL
        assert isinstance(
            router._samplers[SamplingMethod.DEFAULT],
            CombinatorialSampler,
        )

    def test_clone(self, router):
        new_router = router.clone()
        assert (
            new_router._samplers[SamplingMethod.RANDOM]
            is router._samplers[SamplingMethod.RANDOM]
        )
        assert (
            new_router._samplers[SamplingMethod.COMBINATORIAL]
            is router._samplers[SamplingMethod.COMBINATORIAL]
        )
        assert (
            new_router._samplers[SamplingMethod.CYCLICAL]
            is router._samplers[SamplingMethod.CYCLICAL]
        )
        assert (
            new_router._samplers[SamplingMethod.DEFAULT]
            is router._samplers[SamplingMethod.DEFAULT]
        )
