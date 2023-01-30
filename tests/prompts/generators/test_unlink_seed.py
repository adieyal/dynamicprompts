from dynamicprompts.generators.randomprompt import RandomPromptGenerator


class TestUnlinkSeedFromPrompt:
    def test_no_unlink_seed_from_prompt(self, wildcard_manager):
        generator = RandomPromptGenerator(
            wildcard_manager,
            unlink_seed_from_prompt=False,
        )
        assert generator._unlink_seed_from_prompt is False

        for i in range(5):
            generator = RandomPromptGenerator(
                wildcard_manager,
                unlink_seed_from_prompt=False,
                seed=0,
            )
            prompt = "I love {1-2$$red|green|blue}"

            prompts = list(generator.generate(prompt, 5))
            first_prompts = prompts

            for i in range(10):
                generator = RandomPromptGenerator(
                    wildcard_manager,
                    unlink_seed_from_prompt=False,
                    seed=0,
                )
                prompts = list(generator.generate(prompt, 5))
                assert prompts == first_prompts

    def test_unlink_seed_from_prompt(self, wildcard_manager):
        generator = RandomPromptGenerator(
            wildcard_manager,
            unlink_seed_from_prompt=True,
        )
        assert generator._unlink_seed_from_prompt is True

        for i in range(5):
            generator = RandomPromptGenerator(
                wildcard_manager,
                unlink_seed_from_prompt=True,
                seed=0,
            )
            prompt = "I love {1-2$$red|green|blue}"

            prompts = list(generator.generate(prompt, 20))
            first_prompts = prompts

            for i in range(10):
                generator = RandomPromptGenerator(
                    wildcard_manager,
                    unlink_seed_from_prompt=True,
                    seed=0,
                )
                prompts = list(generator.generate(prompt, 20))
                assert prompts != first_prompts
