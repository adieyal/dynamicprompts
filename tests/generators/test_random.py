from collections import Counter
from unittest.mock import patch

import pytest
from dynamicprompts.generators.randomprompt import RandomPromptGenerator
from dynamicprompts.wildcards import WildcardManager

from tests.samplers.utils import (
    patch_random_sampler_variant_choices_with_literals,
    patch_random_sampler_wildcard_choice,
)


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
        prompt = "I saw a __animals/mammals/*__"  # refers to a real wildcard
        animals = ["dog", "dog", "wolf", "tiger"]  # ... but we'll mock it

        with patch_random_sampler_wildcard_choice(animals):
            prompts = list(generator.generate(prompt, 4))

        assert [str(p) for p in prompts] == [f"I saw a {animal}" for animal in animals]

    def test_wildcard_values_preserve_literal_openers_and_escapes(self, tmp_path):
        wildcard_file = tmp_path / "parser-literals.yaml"
        wildcard_file.write_text(
            "- '$0'\n- '\\{braces\\}'\n- 'unknown \\q escape'\n",
        )
        generator = RandomPromptGenerator(WildcardManager(path=tmp_path))
        expected = ["$0", "{braces}", r"unknown \q escape"]
        with patch_random_sampler_wildcard_choice(
            ["$0", r"\{braces\}", r"unknown \q escape"],
        ):
            prompts = list(generator.generate("__parser-literals__", 3))

        assert list(map(str, prompts)) == expected

    def test_variant_values_preserve_unescaped_dollars(self, tmp_path):
        wildcard_file = tmp_path / "parser-dollars.yaml"
        wildcard_file.write_text("- '{$0|x}'\n- '{$10|x}'\n- '{$tephanie|x}'\n")
        generator = RandomPromptGenerator(WildcardManager(path=tmp_path))

        with patch_random_sampler_wildcard_choice(
            ["{$0|x}", "{$10|x}", "{$tephanie|x}"],
        ):
            with patch_random_sampler_variant_choices_with_literals(
                ["$0", "$10", "$tephanie"],
            ):
                prompts = list(generator.generate("__parser-dollars__", 3))

        assert list(map(str, prompts)) == ["$0", "$10", "$tephanie"]

    def test_without_wildcard_manager(self):
        generator = RandomPromptGenerator()
        assert generator._context.wildcard_manager.path is None

    def test_generate_with_seeds_wrong_length(self, generator: RandomPromptGenerator):
        with pytest.raises(ValueError) as exc_info:
            generator.generate(num_images=3, seeds=[42, 44])
        assert str(exc_info.value) == "Expected 3 seeds, but got 2"

    def test_generate_with_template_and_seeds(self, generator: RandomPromptGenerator):
        with patch.object(generator._context.rand, "seed", autospec=True) as mock_seed:
            generator.generate(template="test_template", num_images=2, seeds=[42, 43])

            mock_seed.assert_any_call(42)
            mock_seed.assert_any_call(43)

    def test_generate_with_one_seed(self, generator: RandomPromptGenerator):
        with patch.object(generator._context.rand, "seed", autospec=True) as mock_seed:
            generator.generate(template="test_template", num_images=2, seeds=[42])

            mock_seed.assert_any_call(42)
            assert mock_seed.call_count == 2
            assert mock_seed.call_args_list[0] == mock_seed.call_args_list[1]

    def test_generate_with_int_seed(self, generator: RandomPromptGenerator):
        with patch.object(generator._context.rand, "seed", autospec=True) as mock_seed:
            generator.generate(template="test_template", num_images=2, seeds=42)

            mock_seed.assert_any_call(42)
            assert mock_seed.call_count == 2
            assert mock_seed.call_args_list[0] == mock_seed.call_args_list[1]

    def test_cyclical_sampler_with_seeds(self, generator: RandomPromptGenerator):
        template = "A {@red|green|blue} ball"
        prompts = generator.generate(template=template, num_images=3, seeds=[1, 2, 3])
        assert [str(p) for p in prompts] == [
            "A red ball",
            "A green ball",
            "A blue ball",
        ]

    def test_weighted_wildcard(self, generator: RandomPromptGenerator):
        prompt = "I saw a __weighted-animals/heavy__"
        prompts = Counter(generator.generate(prompt, 1500))
        # Over 1500 generations with a non-biased RNG we should always the correct order...
        assert [s for s, n in prompts.most_common()] == [
            "I saw a elephant",
            "I saw a rhino",
            "I saw a hippo",
            "I saw a giraffe",
        ]
