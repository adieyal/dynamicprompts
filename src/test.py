# from pathlib import Path
#
# from dynamicprompts.enums import SamplingMethod
# from dynamicprompts.sampler_routers.concrete_sampler_router import ConcreteSamplerRouter
# from dynamicprompts.wildcardmanager import WildcardManager
#
# router = ConcreteSamplerRouter(
#    wildcard_manager=WildcardManager(Path("/tmp/")),
#    default_sampling_method=SamplingMethod.COMBINATORIAL,
# )
#
# prompts = router.sample_prompts(
#    "Hello {red|green|blue} {@slippery|rough} {~pinball|tennis ball|soccer ball} ", 10
# )
#
##print(list(prompts))
## CombinatorialSampler(wildcard_manager=WildcardManager("/tmp/"))
