import random

import pytest
from dynamicprompts.generators.randomprompt import RandomPromptGenerator


@pytest.mark.parametrize("unlink_seed_from_prompt", [True, False])
def test_unlink_seed_from_prompt(wildcard_manager, unlink_seed_from_prompt: bool):
    for i in range(5):
        seed = random.randint(0, 1000000)
        generator = RandomPromptGenerator(
            wildcard_manager,
            unlink_seed_from_prompt=unlink_seed_from_prompt,
            seed=seed,
        )
        prompt = "I love {1-2$$red|green|blue}"

        prompts = list(generator.generate(prompt, 20))
        first_prompts = prompts

        for i in range(5):
            generator = RandomPromptGenerator(
                wildcard_manager,
                unlink_seed_from_prompt=unlink_seed_from_prompt,
                seed=seed,
            )
            prompts = list(generator.generate(prompt, 20))

            assert (prompts == first_prompts) != unlink_seed_from_prompt
