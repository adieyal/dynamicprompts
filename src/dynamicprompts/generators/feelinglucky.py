from __future__ import annotations

import logging
import random

from dynamicprompts.generators.dummygenerator import DummyGenerator
from dynamicprompts.generators.promptgenerator import (
    GeneratorException,
    PromptGenerator,
)

logger = logging.getLogger(__name__)


def query_lexica(query) -> dict:
    try:
        import requests
    except ImportError as ie:
        raise GeneratorException(
            "Could not import `requests`, Feeling Lucky generator will not work. "
            "Install with `pip install dynamicprompts[feelinglucky]` or "
            "`pip install requests`",
        ) from ie
    url = f"https://lexica.art/api/v1/search?q={query}"
    logger.info(f"Requesting {url}")
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


class FeelingLuckyGenerator(PromptGenerator):
    _generator: PromptGenerator

    def __init__(self, generator: PromptGenerator | None = None, **kwargs) -> None:
        if generator is None:
            self._generator = DummyGenerator()
        else:
            self._generator = generator

    def generate(self, search_query: str, num_prompts: int, **kwargs) -> list[str]:
        search_query = self._generator.generate(search_query, 1, **kwargs)[0]

        if search_query.strip() == "":
            query = str(random.randint(0, 10000000))
        else:
            query = search_query

        try:
            data = query_lexica(query)
            prompts = data["images"]
            selected_prompts = random.choices(prompts, k=num_prompts)
            return [p["prompt"] for p in selected_prompts]
        except Exception as e:
            raise GeneratorException(f"Error while generating prompt: {e}") from e
