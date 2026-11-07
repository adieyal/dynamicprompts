from __future__ import annotations

import random
from unittest.mock import patch

import jinja2
import pytest
from dynamicprompts.generators.jinjagenerator import JinjaGenerator
from dynamicprompts.generators.promptgenerator import GeneratorException
from dynamicprompts.parser.config import ParserConfig
from dynamicprompts.wildcards import WildcardManager
from dynamicprompts.wildcards.values import WildcardValues

pytest.importorskip("jinja2")

GET_VALUES = "dynamicprompts.wildcards.wildcard_manager.WildcardManager.get_values"


def _stub_env() -> jinja2.Environment:
    env = jinja2.Environment()
    env.globals["rand"] = random.Random()
    return env


@pytest.fixture
def generator(wildcard_manager: WildcardManager) -> JinjaGenerator:
    config = ParserConfig(wildcard_wrap=wildcard_manager.wildcard_wrap)
    return JinjaGenerator(wildcard_manager, parser_config=config)


class TestJinjaGenerator:
    def test_literal_prompt(self, generator: JinjaGenerator):
        template = "This is a literal prompt"
        assert generator.generate(template) == [template]

    def test_choice_prompt(self, generator: JinjaGenerator):
        with patch("random.Random.choice") as mock_choice:
            mock_choice.side_effect = ["red", "blue", "red"]
            template = "This is a {{ choice('red', 'blue') }} rose"

            assert generator.generate(template, 3) == [
                "This is a red rose",
                "This is a blue rose",
                "This is a red rose",
            ]

    def test_two_choice_prompt(self, generator: JinjaGenerator):
        with patch("random.Random.choice") as mock_choice:
            mock_choice.side_effect = ["red", "triangle", "blue", "square"]
            template = "This is a {{ choice('red', 'blue') }} {{ choice('triangle', 'square') }}"
            assert generator.generate(template, 2) == [
                "This is a red triangle",
                "This is a blue square",
            ]

    def test_prompt_block(self, generator: JinjaGenerator):
        template = """
        {% for colour in ['red', 'blue', 'green'] %}
            {% prompt %}My favourite colour is {{ colour }}{% endprompt %}
        {% endfor %}
        """
        assert generator.generate(template) == [
            "My favourite colour is red",
            "My favourite colour is blue",
            "My favourite colour is green",
        ]

    def test_prompt_block_multiple(self, generator: JinjaGenerator):
        template = """
        {% for colour in ['red', 'blue', 'green'] %}
            {% prompt %}My favourite colour is {{ colour }}{% endprompt %}
        {% endfor %}
        """

        # Results are duplicated because of `2` in `generate(template, 2)`
        assert generator.generate(template, 2) == [
            "My favourite colour is red",
            "My favourite colour is blue",
            "My favourite colour is green",
            "My favourite colour is red",
            "My favourite colour is blue",
            "My favourite colour is green",
        ]

    def test_limit_prompts(self, wildcard_manager: WildcardManager):
        generator = JinjaGenerator(wildcard_manager, limit_prompts=True)
        template = """
        {% for colour in ['red', 'blue', 'green'] %}
            {% prompt %}My favourite colour is {{ colour }}{% endprompt %}
        {% endfor %}
        """

        assert generator.generate(template, 2) == [
            "My favourite colour is red",
            "My favourite colour is blue",
        ]

    @pytest.mark.parametrize("wrapped", [False, True])
    def test_wildcards(
        self,
        generator: JinjaGenerator,
        wildcard_manager: WildcardManager,
        wrapped: bool,
    ):
        wildcard = "colors-cold"
        if wrapped:
            wildcard = wildcard_manager.to_wildcard(wildcard)
        template = f"""
        {{% for colour in wildcard("{wildcard}") %}}
            {{% prompt %}}My favourite colour is {{{{ colour }}}}{{% endprompt %}}
        {{% endfor %}}
        """

        assert generator.generate(template) == [
            "My favourite colour is blue",
            "My favourite colour is green",
        ]

    def test_nested_wildcards(
        self,
        generator: JinjaGenerator,
        wildcard_manager: WildcardManager,
    ):
        wildcard = wildcard_manager.to_wildcard("colours")
        template = f"""
        {{% for colour in wildcard("{wildcard}") %}}
            {{% prompt %}}My favourite colour is {{{{ colour }}}}{{% endprompt %}}
        {{% endfor %}}
        """

        with patch(GET_VALUES) as mock_values:
            mock_values.side_effect = [
                WildcardValues.from_items(i)
                for i in (
                    [
                        "pink",
                        "yellow",
                        wildcard_manager.to_wildcard("blacks"),
                        "purple",
                    ],
                    ["black", "grey"],
                )
            ]

            assert generator.generate(template) == [
                "My favourite colour is pink",
                "My favourite colour is yellow",
                "My favourite colour is black",
                "My favourite colour is grey",
                "My favourite colour is purple",
            ]

    def test_deep_nested_wildcards(
        self,
        generator: JinjaGenerator,
        wildcard_manager: WildcardManager,
    ):
        template = f"""
        {{% for colour in wildcard("{wildcard_manager.to_wildcard("colours")}") %}}
            {{% prompt %}}My favourite colour is {{{{ colour }}}}{{% endprompt %}}
        {{% endfor %}}
        """

        with patch(GET_VALUES) as mock_values:
            mock_values.side_effect = [
                WildcardValues.from_items(i)
                for i in (
                    ["pink", "yellow", wildcard_manager.to_wildcard("black"), "purple"],
                    ["black", wildcard_manager.to_wildcard("greys")],
                    ["light grey", "dark grey"],
                )
            ]

            assert generator.generate(template) == [
                "My favourite colour is pink",
                "My favourite colour is yellow",
                "My favourite colour is black",
                "My favourite colour is light grey",
                "My favourite colour is dark grey",
                "My favourite colour is purple",
            ]

    def test_wildcard_with_choice(self, generator: JinjaGenerator):
        # TODO: what is this test for?
        template = """
        {% prompt %}My favourite colour is {{ choice(wildcard("__colours__")) }}{% endprompt %}
        """

        with patch("random.Random.choice") as mock_choice:
            mock_choice.return_value = "yellow"

            assert generator.generate(template) == ["My favourite colour is yellow"]

    def test_random_sample(self, generator: JinjaGenerator):
        template = """
        {% prompt %}Test prompt: {{ random_sample("A {red|blue|green} {rose|daisy}") }}{% endprompt %}
        """

        template = """
        {% prompt %}Test prompt: {{ random_sample("A {blue} {daisy}") }}{% endprompt %}
        """
        assert generator.generate(template) == ["Test prompt: A blue daisy"]

    def test_all_combinations(self, generator: JinjaGenerator):
        template = """
        {% for prompt in all_combinations("A {red|blue|green} {rose|daisy}") %}
            {% prompt %}{{ prompt }}{% endprompt %}
        {% endfor %}
        """

        assert generator.generate(template) == [
            "A red rose",
            "A red daisy",
            "A blue rose",
            "A blue daisy",
            "A green rose",
            "A green daisy",
        ]

    def test_invalid_syntax_throws_exception(self, generator: JinjaGenerator):
        template = """
        {% for colour in wildcard("__colours__") %}
            {% prompt %}My favourite colour is {{ colour }}{% endprompt %}
        """

        with pytest.raises(GeneratorException):
            generator.generate(template)

    def test_random(self, generator, monkeypatch):
        from dynamicprompts.jinja_extensions import DYNAMICPROMPTS_FUNCTIONS

        monkeypatch.setitem(DYNAMICPROMPTS_FUNCTIONS, "random", lambda: 0.3)
        template = """
        {% prompt %}My favourite number is {{ random() }}{% endprompt %}
        """

        assert generator.generate(template) == ["My favourite number is 0.3"]

    def test_choice(self, generator: JinjaGenerator):
        with patch("random.Random.choice") as mock_choice:
            mock_choice.return_value = "red"
            template = """
            {% prompt %}My favourite color is {{ choice("red", "green", "orange") }}{% endprompt %}
            """
            assert generator.generate(template) == ["My favourite color is red"]

    def test_weighted_choice(self, generator: JinjaGenerator):
        with patch("random.Random.choices") as mock_choice:
            mock_choice.side_effect = [["yellow"]]
            template = """My favourite colour is {{ weighted_choice(("pink", 0.2), ("yellow", 0.3), ("black", 0.4), ("purple", 0.1)) }}"""

            assert generator.generate(template) == ["My favourite colour is yellow"]
            assert mock_choice.call_args[0][0] == ("pink", "yellow", "black", "purple")
            assert mock_choice.call_args[1]["weights"] == (0.2, 0.3, 0.4, 0.1)

    def test_flip_coin(self, generator: JinjaGenerator):
        with patch("random.Random.choice", return_value="caught") as mock_choice:
            prompts = generator.generate(
                "A {{ flip_coin('caught', 'fleeing') }} Pikachu",
            )

        assert prompts == ["A caught Pikachu"]
        mock_choice.assert_called_once_with(("caught", "fleeing"))

    def test_pick_multiple(self, generator: JinjaGenerator):
        with patch(
            "random.Random.sample",
            return_value=["Misty", "Brock"],
        ) as mock_sample:
            prompts = generator.generate(
                "{{ pick_multiple(['Ash', 'Misty', 'Brock'], 2)|join(' and ') }}",
            )

        assert prompts == ["Misty and Brock"]
        mock_sample.assert_called_once_with(["Ash", "Misty", "Brock"], 2)

    def test_pick_multiple_defaults_to_random_non_empty_length(self):
        from dynamicprompts.jinja_extensions import pick_multiple

        with patch("random.Random.randint", return_value=2) as mock_randint, patch(
            "random.Random.sample",
            return_value=["Misty", "Brock"],
        ):
            result = pick_multiple(_stub_env(), iter(["Ash", "Misty", "Brock"]))

        assert result == ["Misty", "Brock"]
        mock_randint.assert_called_once_with(1, 3)

    def test_pick_multiple_empty_iterable(self):
        from dynamicprompts.jinja_extensions import pick_multiple

        assert pick_multiple(_stub_env(), iter(())) == []

    def test_pick_multiple_caps_length_to_available_items(self):
        from dynamicprompts.jinja_extensions import pick_multiple

        assert pick_multiple(_stub_env(), iter(["Ash", "Misty"]), 3) == ["Ash", "Misty"]

    def test_pick_multiple_rejects_negative_length(self):
        from dynamicprompts.jinja_extensions import pick_multiple

        with pytest.raises(ValueError, match="must not be negative"):
            pick_multiple(_stub_env(), ["Ash"], -1)

    def test_permutations(self, generator: JinjaGenerator):
        template = """
        {% for val in permutations(["red", "green", "blue"], 1, 2) %}
            {% prompt %}My favourite colours are {{ val|join(' and ') }}{% endprompt %}
        {% endfor %}
        """

        assert generator.generate(template) == [
            "My favourite colours are red",
            "My favourite colours are green",
            "My favourite colours are blue",
            "My favourite colours are red and green",
            "My favourite colours are red and blue",
            "My favourite colours are green and red",
            "My favourite colours are green and blue",
            "My favourite colours are blue and red",
            "My favourite colours are blue and green",
        ]

    def test_ignore_whitespace(self, generator: JinjaGenerator):
        template = """
        {% for colour in ['red', 'blue', 'green'] %}
            {% prompt %}My favourite colour is
              {{ colour }}{% endprompt %}
        {% endfor %}
        """

        prompts = generator.generate(template)
        for p in prompts:
            assert "\n" in p

        generator = JinjaGenerator(ignore_whitespace=True)
        prompts = generator.generate(template)
        for p in prompts:
            assert "\n" not in p

    def test_jinja_template_from_file(self, generator: JinjaGenerator):
        template = """
        {%- import 'jinja/lib.jinja' as lib -%}
        {{ lib.echo('test') -}}
        """
        assert generator.generate(template) == ["test"]

        with patch("random.Random.choice") as mock_choice:
            mock_choice.side_effect = ["red", "blue", "red"]
            template = """
            {%- import 'jinja/lib.jinja' as lib with context -%}
            {{ lib.mychoice() -}}
            """

            assert generator.generate(template, 3) == [
                "This is a red rose",
                "This is a blue rose",
                "This is a red rose",
            ]

    @pytest.mark.parametrize("template_name", ["../README.md", "/etc/hostname"])
    def test_jinja_templates_cannot_leave_wildcard_folder(
        self,
        generator: JinjaGenerator,
        template_name: str,
    ):
        import jinja2

        with pytest.raises(jinja2.TemplateNotFound):
            generator.generate(f"{{% include '{template_name}' %}}")


SEEDED_TEMPLATES = [
    "{{ choice('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h') }}",
    "{{ ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']|random }}",
    "{{ pick_multiple(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'], 3)|join(',') }}",
    "{{ random_sample('{a|b|c|d|e|f|g|h}') }}",
    "{{ randint(1, 1000000) }} {{ random() }}",
]


class TestJinjaSeeds:
    @pytest.mark.parametrize("template", SEEDED_TEMPLATES)
    def test_same_seed_same_output(self, generator: JinjaGenerator, template: str):
        first = generator.generate(template, 5, seeds=[1, 2, 3, 4, 5])
        second = generator.generate(template, 5, seeds=[1, 2, 3, 4, 5])
        assert first == second

    def test_single_seed_is_repeated(self, generator: JinjaGenerator):
        prompts = generator.generate("{{ randint(1, 1000000) }}", 3, seeds=7)
        assert len(set(prompts)) == 1

    @pytest.mark.parametrize("template", SEEDED_TEMPLATES)
    def test_different_seeds_can_differ(
        self,
        generator: JinjaGenerator,
        template: str,
    ):
        prompts = generator.generate(template, 5, seeds=[1, 2, 3, 4, 5])
        assert len(set(prompts)) > 1

    def test_seeds_length_mismatch(self, generator: JinjaGenerator):
        with pytest.raises(ValueError, match="Expected 3 seeds, but got 2"):
            generator.generate("x", 3, seeds=[1, 2])

    def test_unlink_seed_ignores_seeds(self, wildcard_manager: WildcardManager):
        generator = JinjaGenerator(wildcard_manager, unlink_seed_from_prompt=True)
        prompts = generator.generate("{{ randint(1, 10**12) }}", 3, seeds=1)
        assert len(set(prompts)) > 1

    def test_global_random_state_untouched(self, generator: JinjaGenerator):
        template = (
            "{{ choice('a', 'b') }} {{ ['a', 'b']|random }} "
            "{{ pick_multiple(['a', 'b', 'c']) }} {{ random() }} "
            "{{ random_sample('{a|b}') }}"
        )
        state = random.getstate()
        generator.generate(template, 3, seeds=[1, 2, 3])
        assert random.getstate() == state
