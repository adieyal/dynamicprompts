import pytest
from dynamicprompts.generators.randomprompt import RandomPromptGenerator
from dynamicprompts.wildcards import WildcardManager

from tests.samplers.utils import patch_random_sampler_wildcard_choice


@pytest.fixture
def generator(wildcard_manager: WildcardManager) -> RandomPromptGenerator:
    return RandomPromptGenerator(wildcard_manager)


class TestRandomGenerator:
    def test_literal_template(self, generator):
        prompt = "I love bread"

        prompts = list(generator.generate(prompt, 10))

        assert len(prompts) == 10
        assert prompts[0] == prompt

    def test_generate_with_wildcard(self, generator):
        prompt = "I saw a __mammals/*__"
        animals = ["dog", "dog", "wolf", "tiger"]

        with patch_random_sampler_wildcard_choice(animals):
            prompts = list(generator.generate(prompt, 4))

        assert prompts == [f"I saw a {animal}" for animal in animals]

    def test_without_wildcard_manager(self):
        generator = RandomPromptGenerator()
        assert generator._context.wildcard_manager.path is None
