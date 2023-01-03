from unittest import mock

from dynamicprompts.generators.combinatorial import CombinatorialPromptGenerator
class TestCombinatorialGenerator:
    def test_literal_template(self):

        wildcard_manager = mock.Mock()

        generator = CombinatorialPromptGenerator(wildcard_manager, "I love bread")

        prompts = generator.generate(10)

        assert len(prompts) == 1

    def test_generate_with_wildcard(self):
        wildcard_manager = mock.Mock()

        generator = CombinatorialPromptGenerator(wildcard_manager, "I love __food__")

        wildcard_manager.get_all_values.return_value = ["bread", "butter", "cheese"]
        prompts = generator.generate(10)

        assert len(prompts) == 3
        assert prompts[0] == "I love bread"
        assert prompts[1] == "I love butter"
        assert prompts[2] == "I love cheese"
        
        

        