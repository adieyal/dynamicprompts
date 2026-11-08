from unittest.mock import Mock

from dynamicprompts.generators.combinatorial import CombinatorialPromptGenerator
from dynamicprompts.wildcards import WildcardManager
from dynamicprompts.wildcards.values import WildcardValues


class TestCombinatorialGenerator:
    def test_literal_template(self, wildcard_manager: WildcardManager):
        prompt = "I love bread"

        generator = CombinatorialPromptGenerator(wildcard_manager)

        prompts = list(generator.generate(prompt, 10))
        assert prompts == [prompt]

    def test_generate_with_wildcard(self, wildcard_manager: WildcardManager):
        prompt = "I love __food__"

        generator = CombinatorialPromptGenerator(wildcard_manager)

        wildcard_manager.get_values = Mock(
            return_value=WildcardValues.from_items(["bread", "butter", "cheese"]),
        )
        prompts = list(generator.generate(prompt, 10))

        assert prompts == [
            "I love bread",
            "I love butter",
            "I love cheese",
        ]

        prompts = list(generator.generate(prompt, 2))

        assert prompts == [
            "I love bread",
            "I love butter",
        ]

    def test_wildcard_values_preserve_literal_openers_and_escapes(
        self,
        tmp_path,
    ):
        wildcard_file = tmp_path / "parser-literals.yaml"
        wildcard_file.write_text(
            "- '$0'\n- '\\{braces\\}'\n- 'unknown \\q escape'\n",
        )
        wildcard_manager = WildcardManager(path=tmp_path)
        generator = CombinatorialPromptGenerator(wildcard_manager)

        assert list(generator.generate("__parser-literals__")) == [
            "$0",
            "{braces}",
            r"unknown \q escape",
        ]

    def test_variant_values_preserve_unescaped_dollars(self, tmp_path):
        wildcard_file = tmp_path / "parser-dollars.yaml"
        wildcard_file.write_text("- '{$0|x}'\n- '{$10|x}'\n- '{$tephanie|x}'\n")
        generator = CombinatorialPromptGenerator(WildcardManager(path=tmp_path))

        assert list(generator.generate("__parser-dollars__")) == [
            "$0",
            "x",
            "$10",
            "x",
            "$tephanie",
            "x",
        ]

    def test_generate_variant_with_separator(self, wildcard_manager: WildcardManager):
        prompt = "{2$$ and $$A|B|C}"
        generator = CombinatorialPromptGenerator(wildcard_manager)

        prompts = list(generator.generate(prompt))
        assert prompts == [
            "A and B",
            "A and C",
            "B and A",
            "B and C",
            "C and A",
            "C and B",
        ]

    def test_generate_variant_with_pipe_separator(
        self,
        wildcard_manager: WildcardManager,
    ):
        prompt = "{2$$|$$A|B|C}"
        generator = CombinatorialPromptGenerator(wildcard_manager)

        prompts = list(generator.generate(prompt, 9))
        assert prompts == [
            "A|B",
            "A|C",
            "B|A",
            "B|C",
            "C|A",
            "C|B",
        ]

    def test_all_generations(self, wildcard_manager: WildcardManager):
        prompt = "I love __food__ and __drink__"

        generator = CombinatorialPromptGenerator(wildcard_manager)

        wildcard_manager.get_values = Mock(
            return_value=WildcardValues.from_items(["bread", "butter", "cheese"]),
        )
        for limit in (None, 9):
            prompts = list(generator.generate(prompt, limit))

            assert prompts == [
                "I love bread and bread",
                "I love bread and butter",
                "I love bread and cheese",
                "I love butter and bread",
                "I love butter and butter",
                "I love butter and cheese",
                "I love cheese and bread",
                "I love cheese and butter",
                "I love cheese and cheese",
            ]

    def test_without_wildcard_manager(self):
        generator = CombinatorialPromptGenerator()
        assert generator._context.wildcard_manager.path is None


def test_generate_accepts_kwargs():
    generator = CombinatorialPromptGenerator()
    generator.generate("template", max_prompts=5, extra_arg="value")
    # shouldn't raise an exception


def test_seed_makes_random_choices_repeatable():
    template = "{~a|b|c|d|e|f|g|h} {x|y}"
    first = CombinatorialPromptGenerator(seed=3).generate(template)
    runs = {
        tuple(CombinatorialPromptGenerator(seed=3).generate(template)) for _ in range(5)
    }
    assert runs == {tuple(first)}
    others = {
        tuple(CombinatorialPromptGenerator(seed=seed).generate(template))
        for seed in range(10)
    }
    assert len(others) > 1
