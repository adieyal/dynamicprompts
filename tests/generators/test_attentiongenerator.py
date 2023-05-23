from unittest.mock import MagicMock

import pytest
from dynamicprompts.generators.attentiongenerator import (
    AttentionGenerator,
    cheap_chunker,
)


@pytest.fixture
def generator():
    return AttentionGenerator()


def test_cheap_chunker():
    assert cheap_chunker(
        "purple cat singing opera, artistic, painting (best quality:1.3)",
    ) == [
        "purple cat singing opera",
        "artistic",
        "painting",
        "best quality",
    ]


@pytest.mark.slow
def test_default_generator(generator):
    prompt_words = ["purple", "artistic", "painting"]
    for generated_prompt in generator.generate(
        "purple cat singing opera, artistic, painting",
        5,
    ):
        assert any(
            f"({word}" in generated_prompt for word in prompt_words
        ), f"Expected one of {prompt_words} in generated prompt, but got: {generated_prompt}"
        assert (
            ")" in generated_prompt
        ), f"Expected ')' in generated prompt, but got: {generated_prompt}"


@pytest.mark.slow
def test_generate_accepts_kwargs():
    # Create a MagicMock instance for _prompt_generator
    mock_prompt_generator = MagicMock()

    # Initialize the AttentionGenerator with the mocked _prompt_generator
    generator = AttentionGenerator()
    generator._generator = mock_prompt_generator

    # Define test kwargs
    test_kwargs = {"arg1": "value1", "arg2": "value2"}

    # Call the generate method with kwargs
    _ = list(generator.generate("test prompt", 5, **test_kwargs))

    # Assert that the _prompt_generator's generate method was called with the correct arguments
    mock_prompt_generator.generate.assert_called_with("test prompt", 5, **test_kwargs)
