from unittest import mock

import pytest
from dynamicprompts.generators.combinatorial import CombinatorialPromptGenerator
from dynamicprompts.wildcardmanager import WildcardManager


@pytest.fixture
def wildcard_manager():
    return mock.Mock()


class TestCombinatorialGenerator:
    def test_literal_template(self, wildcard_manager):
        prompt = "I love bread"

        generator = CombinatorialPromptGenerator(wildcard_manager)

        prompts = list(generator.generate(prompt, 10))

        assert len(prompts) == 1
        assert prompts[0] == prompt

    def test_generate_with_wildcard(self, wildcard_manager):
        prompt = "I love __food__"

        generator = CombinatorialPromptGenerator(wildcard_manager)

        wildcard_manager.get_all_values.return_value = ["bread", "butter", "cheese"]
        prompts = list(generator.generate(prompt, 10))

        assert len(prompts) == 3
        assert prompts[0] == "I love bread"
        assert prompts[1] == "I love butter"
        assert prompts[2] == "I love cheese"


        prompts = list(generator.generate(prompt, 2))

        assert len(prompts) == 2
        assert prompts[0] == "I love bread"
        assert prompts[1] == "I love butter"

    def test_all_generations(self, wildcard_manager):
        prompt = "I love __food__ and __drink__"

        generator = CombinatorialPromptGenerator(wildcard_manager)

        wildcard_manager.get_all_values.return_value = ["bread", "butter", "cheese"]
        prompts = list(generator.generate(prompt, None))

        assert len(prompts) == 9
        assert prompts[0] == "I love bread and bread"
        assert prompts[1] == "I love bread and butter"
        assert prompts[2] == "I love bread and cheese"
        assert prompts[3] == "I love butter and bread"
        assert prompts[4] == "I love butter and butter"
        assert prompts[5] == "I love butter and cheese"
        assert prompts[6] == "I love cheese and bread"
        assert prompts[7] == "I love cheese and butter"
        assert prompts[8] == "I love cheese and cheese"

        prompts = generator.generate(prompt)

        assert len(list(prompts)) == 9


        
        

        
