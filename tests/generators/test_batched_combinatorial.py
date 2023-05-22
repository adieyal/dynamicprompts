from dynamicprompts import constants
from dynamicprompts.generators.batched_combinatorial import (
    BatchedCombinatorialPromptGenerator,
)
from dynamicprompts.generators.promptgenerator import PromptGenerator


def test_single_batch(mocker):
    mock_generator = mocker.MagicMock(PromptGenerator)
    mock_generator.generate.return_value = ["image1", "image2"]
    generator = BatchedCombinatorialPromptGenerator(mock_generator, batches=1)
    images = generator.generate("template")
    assert images == ["image1", "image2"]
    mock_generator.generate.assert_called_once_with("template", constants.MAX_IMAGES)


def test_multiple_batches(mocker):
    mock_generator = mocker.MagicMock(PromptGenerator)
    mock_generator.generate.return_value = ["image1", "image2"]
    generator = BatchedCombinatorialPromptGenerator(mock_generator, batches=3)
    images = generator.generate("template")
    assert images == ["image1", "image2", "image1", "image2", "image1", "image2"]
    assert mock_generator.generate.call_count == 3


def test_max_prompts_passed_correctly(mocker):
    mock_generator = mocker.MagicMock(PromptGenerator)
    generator = BatchedCombinatorialPromptGenerator(mock_generator, batches=1)
    generator.generate("template", max_prompts=5)
    mock_generator.generate.assert_called_once_with("template", 5)


def test_generate_accepts_kwargs(mocker):
    mock_generator = mocker.MagicMock(PromptGenerator)
    generator = BatchedCombinatorialPromptGenerator(mock_generator, batches=1)
    generator.generate("template", max_prompts=5, extra_arg="value")
    mock_generator.generate.assert_called_once_with("template", 5, extra_arg="value")
