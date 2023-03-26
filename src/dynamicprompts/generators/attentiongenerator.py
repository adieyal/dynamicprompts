from __future__ import annotations

import logging
import random
from functools import lru_cache

from dynamicprompts.generators.dummygenerator import DummyGenerator
from dynamicprompts.generators.promptgenerator import PromptGenerator
from dynamicprompts.utils import append_chunks, remove_a1111_special_syntax_chunks

logger = logging.getLogger(__name__)

MODEL_NAME = "en_core_web_sm"


class AttentionGenerator(PromptGenerator):
    _prompt_generator: PromptGenerator

    def __init__(
        self,
        generator: PromptGenerator | None = None,
        min_attention: float = 0.1,
        max_attention: float = 0.9,
    ) -> None:
        try:
            import spacy
        except ImportError as ie:
            raise ImportError(
                "Could not import spacy, attention generator will not work. "
                "Install with pip install dynamicprompts[attentiongrabber]",
            ) from ie
        try:
            spacy.load(MODEL_NAME)
        except OSError:
            logger.warning("Spacy model not found, downloading...")
            from spacy.cli.download import download

            download(MODEL_NAME)

        self._nlp = lru_cache(maxsize=64)(spacy.load(MODEL_NAME))

        if generator is None:
            self._prompt_generator = DummyGenerator()
        else:
            self._prompt_generator = generator

        m, M = min(min_attention, max_attention), max(min_attention, max_attention)
        self._min_attention, self._max_attention = m, M

    def _add_emphasis(self, prompt: str) -> str:
        # Grab the special chunks first, so we don't accidentally add emphasis to them
        prompt, special_chunks = remove_a1111_special_syntax_chunks(prompt)

        doc = self._nlp(prompt)
        keywords = list(doc.noun_chunks)
        if len(keywords) == 0:
            return prompt

        keyword = random.choice(keywords)
        attention = round(random.uniform(self._min_attention, self._max_attention), 2)
        prompt = prompt.replace(str(keyword), f"({keyword}:{attention})")

        # Add the special chunks back in
        return append_chunks(prompt, special_chunks)

    def generate(self, *args, **kwargs) -> list[str]:
        prompts = self._prompt_generator.generate(*args, **kwargs)
        new_prompts = [self._add_emphasis(p) for p in prompts]

        return new_prompts
