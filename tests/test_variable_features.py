from itertools import islice

from dynamicprompts.enums import SamplingMethod
from dynamicprompts.parser.parse import parse
from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.wildcards import WildcardManager


def test_discussion_61(wildcard_manager: WildcardManager):
    cmd = parse("${animal={fox|manatee}} __publicprompts/plush-toy__")
    scon = SamplingContext(
        # TODO: a COMBINATORIAL sampling method does not yet propagate
        #       into sampling the expanded wildcard, (IOW, with a
        #       COMBINATORIAL context, this test should also result in
        #       two prompts, one for a fox and one for a manatee).
        default_sampling_method=SamplingMethod.RANDOM,
        wildcard_manager=wildcard_manager,
    )

    gen = scon.sample_prompts(cmd)
    seen = set()
    expected = {"fox", "manatee"}
    for prompt in islice(gen, 10):
        prompt = str(prompt).strip().lower()
        assert prompt.startswith("cute kawaii squishy")
        for ex in expected:
            if ex in prompt:
                seen.add(ex)
        if expected == seen:
            break
    assert seen == expected


def test_discussion_61_shorthand(wildcard_manager: WildcardManager):
    cmd = parse("__publicprompts/plush-toy(animal=fox)__")
    scon = SamplingContext(
        default_sampling_method=SamplingMethod.RANDOM,
        wildcard_manager=wildcard_manager,
    )
    prompt = str(next(scon.sample_prompts(cmd)))
    assert prompt.strip().lower().startswith("cute kawaii squishy fox")
