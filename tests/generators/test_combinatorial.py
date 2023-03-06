from unittest.mock import Mock

from dynamicprompts.generators.combinatorial import CombinatorialPromptGenerator
from dynamicprompts.wildcardmanager import WildcardManager


class TestCombinatorialGenerator:
    def test_literal_template(self, wildcard_manager: WildcardManager):
        prompt = "I love bread"

        generator = CombinatorialPromptGenerator(wildcard_manager)

        prompts = list(generator.generate(prompt, 10))

        assert len(prompts) == 1
        assert prompts[0] == prompt

    def test_generate_with_wildcard(self, wildcard_manager: WildcardManager):
        prompt = "I love __food__"

        generator = CombinatorialPromptGenerator(wildcard_manager)

        wildcard_manager.get_all_values = Mock(
            return_value=["bread", "butter", "cheese"],
        )
        prompts = list(generator.generate(prompt, 10))

        assert len(prompts) == 3
        assert prompts[0] == "I love bread"
        assert prompts[1] == "I love butter"
        assert prompts[2] == "I love cheese"

        prompts = list(generator.generate(prompt, 2))

        assert len(prompts) == 2
        assert prompts[0] == "I love bread"
        assert prompts[1] == "I love butter"

    def test_generate_variant_with_separator(self, wildcard_manager: WildcardManager):
        prompt = "{2$$ and $$A|B|C}"
        generator = CombinatorialPromptGenerator(wildcard_manager)

        prompts = list(generator.generate(prompt))
        assert len(prompts) == 6

        assert prompts[0] == "A and B"
        assert prompts[1] == "A and C"
        assert prompts[2] == "B and A"
        assert prompts[3] == "B and C"
        assert prompts[4] == "C and A"
        assert prompts[5] == "C and B"

    def test_generate_variant_with_pipe_separator(
        self,
        wildcard_manager: WildcardManager,
    ):
        prompt = "{2$$|$$A|B|C}"
        generator = CombinatorialPromptGenerator(wildcard_manager)

        prompts = list(generator.generate(prompt, 9))
        assert len(prompts) == 6

        assert prompts[0] == "A|B"
        assert prompts[1] == "A|C"
        assert prompts[2] == "B|A"
        assert prompts[3] == "B|C"
        assert prompts[4] == "C|A"
        assert prompts[5] == "C|B"

    def test_all_generations(self, wildcard_manager: WildcardManager):
        prompt = "I love __food__ and __drink__"

        generator = CombinatorialPromptGenerator(wildcard_manager)

        wildcard_manager.get_all_values = Mock(
            return_value=["bread", "butter", "cheese"],
        )
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

    def test_without_wildcard_manager(self):
        generator = CombinatorialPromptGenerator()
        assert generator._context.wildcard_manager.path is None
