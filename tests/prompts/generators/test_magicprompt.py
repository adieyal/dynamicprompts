import random
from functools import partial

import pytest

pytest.importorskip("dynamicprompts.generators.magicprompt")


@pytest.mark.slow
class TestMagicPrompt:
    def test_default_generator(self):
        from dynamicprompts.generators.dummygenerator import DummyGenerator
        from dynamicprompts.generators.magicprompt import MagicPromptGenerator

        generator = MagicPromptGenerator()
        assert isinstance(generator._prompt_generator, DummyGenerator)

        CPU = -1
        assert generator._device == CPU


@pytest.mark.parametrize("original_prompt", [
    "Original prompt",
    "[Original|prompt]",
    "{Original|prompt}",
    "Original - prompt",
])
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

    def _generator(orig_prompt: str, max_length: int, temperature: float):
        return [{"generated_text": f"{orig_prompt} {random.choice(all_artists)}"}]

    generator = MagicPromptGenerator(
        # a regexp that will block some of those boring artists.
        blocklist_regex=r"grug ret|plow|ertGa",
    )
    generator._generator = _generator

    original_prompt = "This is a prompt"
    for x in range(len(all_artists) * 2):  # should be enough to try things out
        prompt = generator.generate(original_prompt)
        assert prompt != original_prompt  # Make sure we're not getting the original prompt back
        # Make sure we're not getting any of the blocked artists
        assert not any(artist in prompt for artist in boring_artists)
