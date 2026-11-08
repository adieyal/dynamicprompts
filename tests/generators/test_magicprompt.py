from __future__ import annotations

import os
import random
from functools import partial
from unittest.mock import MagicMock

import pytest

actually_test_transformers = bool(os.environ.get("DP_ACTUALLY_TEST_TRANSFORMERS"))


@pytest.fixture(autouse=True)
def mock_import_transformers(monkeypatch):
    if actually_test_transformers:  # Skip mock import
        return
    from dynamicprompts.generators import magicprompt

    monkeypatch.setattr(magicprompt, "_import_transformers", MagicMock())


def test_default_generator():
    from dynamicprompts.generators.dummygenerator import DummyGenerator
    from dynamicprompts.generators.magicprompt import MagicPromptGenerator

    generator = MagicPromptGenerator()
    assert isinstance(generator._prompt_generator, DummyGenerator)

    if actually_test_transformers:
        prefix = "magical reality photo of a cat in"
        pgen = generator.generate(prefix, max_attempts=5)
        for prompt in pgen:
            print(prompt)  # noqa: T201
            assert prompt.startswith(prefix)


@pytest.mark.parametrize(
    "original_prompt",
    [
        "Original prompt",
        "[Original|prompt]",
        "{Original|prompt}",
        "Original - prompt",
    ],
)
def test_cleanup_magic_prompt(original_prompt: str):
    from dynamicprompts.generators.magicprompt import clean_up_magic_prompt

    clean_up = partial(clean_up_magic_prompt, original_prompt)

    prompt = "- This is a {prompt} xyz"
    cleaned_prompt = clean_up(f"{original_prompt} {prompt}")
    assert cleaned_prompt == f"{original_prompt} This is a (prompt) xyz"

    prompt = " $$ This is a prompt $$"
    cleaned_prompt = clean_up(f"{original_prompt} {prompt}")
    assert cleaned_prompt == f"{original_prompt} This is a prompt"

    prompt = "This ( is ) a prompt"
    cleaned_prompt = clean_up(f"{original_prompt} {prompt}")
    assert cleaned_prompt == f"{original_prompt} This (is) a prompt"

    prompt = "This is - a prompt"
    cleaned_prompt = clean_up(f"{original_prompt} {prompt}")
    assert cleaned_prompt == f"{original_prompt} This is-a prompt"

    prompt = "This is a prompt; another prompt"
    cleaned_prompt = clean_up(f"{original_prompt} {prompt}")
    assert cleaned_prompt == f"{original_prompt} This is a prompt, another prompt"

    prompt = "This is. a prompt; another prompt"
    cleaned_prompt = clean_up(f"{original_prompt} {prompt}")
    assert cleaned_prompt == f"{original_prompt} This is, a prompt, another prompt"

    prompt = "This is a prompt _ another prompt"
    cleaned_prompt = clean_up(f"{original_prompt}{prompt}")
    assert cleaned_prompt == f"{original_prompt} This is a prompt another prompt"

    # TODO
    prompt = "This is a prompt , , another prompt"
    cleaned_prompt = clean_up(f"{original_prompt} {prompt}")
    assert cleaned_prompt == f"{original_prompt} This is a prompt ,, another prompt"

    prompt = "This is a prompt! dddd"
    cleaned_prompt = clean_up(f"{original_prompt} {prompt}")
    assert cleaned_prompt == f"{original_prompt} (This is a prompt:1.1) dddd"

    prompt = "This is a prompt!! dddd"
    cleaned_prompt = clean_up(f"{original_prompt} {prompt}")
    assert cleaned_prompt == f"{original_prompt} (This is a prompt:1.21) dddd"


@pytest.mark.slow
def test_magic_prompt_blocklist():
    from dynamicprompts.generators.magicprompt import MagicPromptGenerator

    boring_artists = [
        "ertgarm",
        "grug retkawsky",
        "plow",
    ]
    all_artists = [
        *boring_artists,
        "akseli gallen-kallela",
        "michael jackson",
        "picasso",
    ]

    def _generator(
        orig_prompts: list[str],
        max_length: int,
        temperature: float,
        **kwargs,
    ):
        return [
            [
                {"generated_text": f"{orig_prompt} {random.choice(all_artists)}"}
                for orig_prompt in orig_prompts
            ],
        ]

    generator = MagicPromptGenerator(
        # a regexp that will block some of those boring artists.
        blocklist_regex=r"grug ret|plow|ertGa",
    )
    generator._generator = _generator

    original_prompt = "This is a prompt"
    for x in range(len(all_artists) * 2):  # should be enough to try things out
        prompts = generator.generate(original_prompt)
        magic_prompt = prompts[0]
        assert (
            magic_prompt != original_prompt
        )  # Make sure we're not getting the original prompt back
        # Make sure we're not getting any of the blocked artists
        assert not any(artist in magic_prompt for artist in boring_artists)


def test_generate_passes_kwargs():
    from dynamicprompts.generators.magicprompt import MagicPromptGenerator

    mock_generator = MagicMock()
    mock_generator.generate.return_value = ["string1", "string2", "string3"]

    generator = MagicPromptGenerator()
    generator._prompt_generator = mock_generator

    kwargs = {"kwarg1": "value1", "kwarg2": "value2"}
    generator.generate("Test prompt", **kwargs)

    mock_generator.generate.assert_called_with("Test prompt", **kwargs)


def test_failed_load_is_retried(monkeypatch):
    from dynamicprompts.generators import magicprompt
    from dynamicprompts.generators.magicprompt import MagicPromptGenerator

    monkeypatch.setattr(MagicPromptGenerator, "generator", None)
    monkeypatch.setattr(MagicPromptGenerator, "_model_name", None)
    transformers = MagicMock()
    transformers.AutoModelForCausalLM.from_pretrained.side_effect = [
        OSError("download failed"),
        MagicMock(),
    ]
    monkeypatch.setattr(magicprompt, "_import_transformers", lambda: transformers)

    with pytest.raises(OSError):
        MagicPromptGenerator()
    assert MagicPromptGenerator._model_name is None

    generator = MagicPromptGenerator()
    assert generator._generator is transformers.pipeline.return_value
    assert transformers.AutoModelForCausalLM.from_pretrained.call_count == 2


def test_max_prompt_length_is_not_overridden():
    from dynamicprompts.generators.magicprompt import MagicPromptGenerator

    pipeline = MagicMock(return_value=[[{"generated_text": "a cat, detailed"}]])
    generator = MagicPromptGenerator(max_prompt_length=42)
    generator._generator = pipeline
    generator.generate("a cat")

    kwargs = pipeline.call_args.kwargs
    assert kwargs["max_length"] == 42
    assert kwargs["max_new_tokens"] is None
