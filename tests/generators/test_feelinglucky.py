from unittest.mock import Mock, patch

import pytest
from dynamicprompts.generators import DummyGenerator, FeelingLuckyGenerator


@pytest.fixture
def mock_generator():
    mock = Mock()
    mock.generate.return_value = ["Prompt"]
    return mock


@pytest.fixture
def mock_requests():
    with patch("dynamicprompts.generators.feelinglucky.query_lexica") as mock:
        mock.return_value = {
            "images": [{"prompt": "ABC"}, {"prompt": "XYZ"}],
        }
        yield mock


@pytest.fixture
def mock_random():
    with patch("dynamicprompts.generators.feelinglucky.random") as mock:
        mock.choices.return_value = [{"prompt": "ABC"}]
        yield mock


def test_default_generator():
    generator = FeelingLuckyGenerator()
    assert isinstance(generator._generator, DummyGenerator)


def test_generate(mock_generator, mock_requests, mock_random):
    generator = FeelingLuckyGenerator(mock_generator)
    prompts = list(generator.generate("This is a test", 1))
    assert prompts == ["ABC"]

    mock_generator.generate.assert_called_with("This is a test", 1)
    mock_random.choices.assert_called_with([{"prompt": "ABC"}, {"prompt": "XYZ"}], k=1)


def test_generate_accepts_kwargs(mock_generator, mock_requests, mock_random):
    generator = FeelingLuckyGenerator(mock_generator)

    # Call generate with an arbitrary keyword argument
    prompts = list(generator.generate("This is a test", 1, some_kwarg="value"))
    assert prompts == ["ABC"]

    # Check that the generate method of the underlying generator was called with the keyword argument
    mock_generator.generate.assert_called_with("This is a test", 1, some_kwarg="value")
    mock_random.choices.assert_called_with([{"prompt": "ABC"}, {"prompt": "XYZ"}], k=1)
