from dynamicprompts.samplers.router import ConcreteSamplerRouter


class TestCombinatorialParent:
    def test_cyclical_variant(
        self,
        combinatorial_sampler_manager: ConcreteSamplerRouter,
    ):
        template = "A {@red|green} ball"
        prompts = list(combinatorial_sampler_manager.sample_prompts(template, 3))

        assert prompts == ["A red ball"]

    def test_variants(self, combinatorial_sampler_manager: ConcreteSamplerRouter):
        template = "A {red|green} {@ball|car}"
        prompts = list(combinatorial_sampler_manager.sample_prompts(template, 3))

        assert prompts == ["A red ball", "A green car"]

        template = "A {@red|green} {ball|car}"
        prompts = list(combinatorial_sampler_manager.sample_prompts(template, 3))

        assert prompts == ["A red ball", "A green car"]

        template = "A {@red|green} {ball|car} {at night|in the morning}"
        prompts = list(combinatorial_sampler_manager.sample_prompts(template, 8))

        assert prompts == [
            "A red ball at night",
            "A green ball in the morning",
            "A red car at night",
            "A green car in the morning",
        ]
