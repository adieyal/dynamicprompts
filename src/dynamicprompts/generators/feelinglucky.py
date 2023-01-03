from __future__ import annotations

import logging
import random

import requests

from dynamicprompts.generators.promptgenerator import PromptGenerator, GeneratorException


logger = logging.getLogger(__name__)

class FeelingLuckyGenerator(PromptGenerator):
    def generate(self, search_query, num_prompts: int) -> list[str]:
        if search_query.strip() == "":
            query = random.randint(0, 10000000)
        else:
            query = search_query

        url = f"https://lexica.art/api/v1/search?q={query}"
        
        try:
            logger.info(f"Requesting {url}")
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            images = data["images"]
            prompts = random.choices(images, k=num_prompts)
            return prompts
        except Exception as e:
            raise GeneratorException("Error while generating prompt: " + str(e))


