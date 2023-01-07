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
