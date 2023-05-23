from __future__ import annotations

import logging
import random
import re
import string
import warnings
from functools import lru_cache
from typing import Callable

from dynamicprompts.generators.dummygenerator import DummyGenerator
from dynamicprompts.generators.promptgenerator import PromptGenerator

logger = logging.getLogger(__name__)


def is_valid_chunk(chunk: str) -> bool:
    if chunk.isdigit():
        return False
    if all(c in string.punctuation for c in chunk):
        return False
    return True


def cheap_chunker(prompt: str) -> list[str]:
    """
    A cheap noun chunker that splits on punctuation and the like.
    """
    return [
        chunk
        for chunk in re.split(r"\s*[,;:.?!()]+\s*", prompt.strip())
        if is_valid_chunk(chunk)
    ]


def get_spacy_chunker(spacy_model_name="en_core_web_sm") -> Callable[[str], list[str]]:
    import spacy

    try:
        spacy.load(spacy_model_name)
    except OSError:
        logger.info("Spacy model not found, downloading...")
        from spacy.cli.download import download

        download(spacy_model_name)
    _nlp = spacy.load(spacy_model_name)
    return lambda prompt: [str(chunk) for chunk in _nlp(prompt).noun_chunks]


@lru_cache(maxsize=1)
def get_chunker() -> Callable[[str], list[str]]:
    """
    Get a noun chunker. If spacy is installed, use that, otherwise use a cheap built-in one.
    """
    try:
        return get_spacy_chunker()
    except ImportError:
        warnings.warn(
            "Could not import spacy, using cheap built-in NLP. "
            "For possibly better results, `pip install spacy`.",
        )
        return cheap_chunker


@lru_cache(maxsize=10)
def find_noun_chunks(text: str) -> tuple[str, ...]:
    """
    Find noun chunks in a string.
    Results are cached; returns an immutable tuple.
    """
    return tuple(get_chunker()(text))


class AttentionGenerator(PromptGenerator):
    _generator: PromptGenerator

    def __init__(
        self,
        generator: PromptGenerator | None = None,
        min_attention: float = 0.1,
        max_attention: float = 0.9,
    ) -> None:
        self._generator = generator or DummyGenerator()
        self._min_attention, self._max_attention = sorted(
            (min_attention, max_attention),
        )

    def _add_emphasis(self, prompt: str) -> str:
        keywords = find_noun_chunks(prompt)
        if not keywords:
            return prompt

        keyword = random.choice(keywords)
        attention = round(random.uniform(self._min_attention, self._max_attention), 2)
        prompt = prompt.replace(str(keyword), f"({keyword}:{attention})")

        return prompt

    def generate(self, *args, **kwargs) -> list[str]:
        prompts = self._generator.generate(*args, **kwargs)
        new_prompts = [self._add_emphasis(p) for p in prompts]

        return new_prompts
