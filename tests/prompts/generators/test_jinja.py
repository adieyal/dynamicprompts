from pathlib import Path
from unittest.mock import patch

import pytest
from dynamicprompts.generators.jinjagenerator import JinjaGenerator
from dynamicprompts.generators.promptgenerator import GeneratorException
from dynamicprompts.wildcardmanager import WildcardManager


@pytest.fixture
def wildcard_manager():
    return WildcardManager(Path("wildcards").absolute())

@pytest.fixture
def generator(wildcard_manager):
    return JinjaGenerator(wildcard_manager)

class TestJinjaGenerator:
    def test_literal_prompt(self, generator):
        template = "This is a literal prompt"
        prompts = generator.generate(template)
        
        assert len(prompts) == 1
        assert prompts[0] == template

    def test_choice_prompt(self, generator):
        with patch('random.choice') as mock_choice:
            mock_choice.side_effect = ["red", "blue", "red"]
            template = "This is a {{ choice('red', 'blue') }} rose"

            prompts = generator.generate(template, 3)
            
            assert len(prompts) == 3
            assert prompts[0] == "This is a red rose"
            assert prompts[1] == "This is a blue rose"
            assert prompts[2] == "This is a red rose"

    def test_two_choice_prompt(self, generator):
        with patch('random.choice') as mock_choice:
            mock_choice.side_effect = ["red", "triangle", "blue", "square"]
            template = "This is a {{ choice('red', 'blue') }} {{ choice('triangle', 'square') }}"
            prompts = generator.generate(template, 2)
            
            assert len(prompts) == 2
            assert prompts[0] == "This is a red triangle"
            assert prompts[1] == "This is a blue square"

    def test_prompt_block(self, generator):
        template = """
        {% for colour in ['red', 'blue', 'green'] %}
            {% prompt %}My favourite colour is {{ colour }}{% endprompt %}
        {% endfor %}
        """

        generator = JinjaGenerator()
        prompts = generator.generate(template)

        assert len(prompts) == 3
        assert prompts[0] == "My favourite colour is red"
        assert prompts[1] == "My favourite colour is blue"
        assert prompts[2] == "My favourite colour is green"

    def test_prompt_block_multiple(self, generator):
        template = """
        {% for colour in ['red', 'blue', 'green'] %}
            {% prompt %}My favourite colour is {{ colour }}{% endprompt %}
        {% endfor %}
        """

        prompts = generator.generate(template, 2)

        assert len(prompts) == 6
        assert prompts[0] == "My favourite colour is red"
        assert prompts[1] == "My favourite colour is blue"
        assert prompts[2] == "My favourite colour is green"
        assert prompts[3] == "My favourite colour is red"
        assert prompts[4] == "My favourite colour is blue"
        assert prompts[5] == "My favourite colour is green"

    def test_wildcards(self, generator):
        template = """
        {% for colour in wildcard("__colours__") %}
            {% prompt %}My favourite colour is {{ colour }}{% endprompt %}
        {% endfor %}
        """

        with patch('dynamicprompts.wildcardmanager.WildcardManager.get_all_values') as mock_values:
            mock_values.return_value = ["pink", "yellow", "black", "purple"]
            prompts = generator.generate(template)

            assert len(prompts) == 4
            assert prompts[0] == "My favourite colour is pink"
            assert prompts[1] == "My favourite colour is yellow"
            assert prompts[2] == "My favourite colour is black"
            assert prompts[3] == "My favourite colour is purple"

    def test_nested_wildcards(self, generator):
        template = """
        {% for colour in wildcard("__colours__") %}
            {% prompt %}My favourite colour is {{ colour }}{% endprompt %}
        {% endfor %}
        """

        with patch('dynamicprompts.wildcardmanager.WildcardManager.get_all_values') as mock_values:
            mock_values.side_effect = (
                ["pink", "yellow", "__blacks__", "purple"],
                ["black", "grey"]
            )

            prompts = generator.generate(template)

            assert len(prompts) == 5
            assert prompts[0] == "My favourite colour is pink"
            assert prompts[1] == "My favourite colour is yellow"
            assert prompts[2] == "My favourite colour is black"
            assert prompts[3] == "My favourite colour is grey"
            assert prompts[4] == "My favourite colour is purple"

    def test_deep_nested_wildcards(self, generator):
        template = """
        {% for colour in wildcard("__colours__") %}
            {% prompt %}My favourite colour is {{ colour }}{% endprompt %}
        {% endfor %}
        """

        with patch('dynamicprompts.wildcardmanager.WildcardManager.get_all_values') as mock_values:
            mock_values.side_effect = (
                ["pink", "yellow", "__blacks__", "purple"],
                ["black", "__greys__"],
                ["light grey", "dark grey"],

            )

            prompts = generator.generate(template)

            assert len(prompts) == 6
            assert prompts[0] == "My favourite colour is pink"
            assert prompts[1] == "My favourite colour is yellow"
            assert prompts[2] == "My favourite colour is black"
            assert prompts[3] == "My favourite colour is light grey"
            assert prompts[4] == "My favourite colour is dark grey"
            assert prompts[5] == "My favourite colour is purple"

    def test_choice_nested_in_wildcards(self, generator):
        template = """
        {% for colour in wildcard("__colours__") %}
            {% prompt %}My favourite colour is {{ colour }}{% endprompt %}
        {% endfor %}
        """

        with patch('dynamicprompts.wildcardmanager.WildcardManager.get_all_values') as mock_values:
            mock_values.side_effect = (
                ["pink", "yellow", "{white|black}", "purple"],
            )

            with patch('random.choice') as mock_choice:
                mock_choice.return_value = "white"

                prompts = generator.generate(template)

                assert len(prompts) == 4
                assert prompts[0] == "My favourite colour is pink"
                assert prompts[1] == "My favourite colour is yellow"
                assert prompts[2] == "My favourite colour is white"
                assert prompts[3] == "My favourite colour is purple"

    def test_wildcard_with_choice(self, generator):
        template = """
        {% prompt %}My favourite colour is {{ choice(wildcard("__colours__")) }}{% endprompt %}
        """

        with patch('dynamicprompts.wildcardmanager.WildcardManager.get_all_values') as mock_values:
            mock_values.return_value = ["pink", "yellow", "black", "purple"]

            with patch('random.choice') as mock_choice:
                mock_choice.return_value = "yellow"

                prompts = generator.generate(template)

                assert len(prompts) == 1
                assert prompts[0] == "My favourite colour is yellow"

    def test_invalid_syntax_throws_exception(self, generator):
        template = """
        {% for colour in wildcard("__colours__") %}
            {% prompt %}My favourite colour is {{ colour }}{% endprompt %}
        """

        with pytest.raises(GeneratorException):
            generator.generate(template)

    def test_random(self, generator):
        with patch('random.random') as mock_choice:
            mock_choice.return_value = 0.3
            template = """
            {% prompt %}My favourite number is {{ random() }}{% endprompt %}
            """

            prompts = generator.generate(template)

            assert len(prompts) == 1
            assert prompts[0] == "My favourite number is 0.3"

    def test_weighted_choice(self, generator):
        with patch('random.choices') as mock_choice:
            mock_choice.side_effect = [["yellow"]]
            template = """My favourite colour is {{ weighted_choice(("pink", 0.2), ("yellow", 0.3), ("black", 0.4), ("purple", 0.1)) }}"""
            
            prompts = generator.generate(template)

            assert len(prompts) == 1
            assert prompts[0] == "My favourite colour is yellow"
            
            assert mock_choice.call_args[0][0] == ("pink", "yellow", "black", "purple")
            assert mock_choice.call_args[1]["weights"] == (0.2, 0.3, 0.4, 0.1)

    def test_permutations(self, generator):
        template = """
        {% for val in permutations(["red", "green", "blue"], 1, 2) %}
            {% prompt %}My favourite colours are {{ val|join(' and ') }}{% endprompt %}
        {% endfor %}
        """

        prompts = generator.generate(template)

        assert len(prompts) == 9
        assert prompts[0] == "My favourite colours are red"
        assert prompts[1] == "My favourite colours are green"
        assert prompts[2] == "My favourite colours are blue"
        assert prompts[3] == "My favourite colours are red and green"
        assert prompts[4] == "My favourite colours are red and blue"
        assert prompts[5] == "My favourite colours are green and red"
        assert prompts[6] == "My favourite colours are green and blue"
        assert prompts[7] == "My favourite colours are blue and red"
        assert prompts[8] == "My favourite colours are blue and green"
