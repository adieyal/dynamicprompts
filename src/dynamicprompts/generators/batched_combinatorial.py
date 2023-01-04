from __future__ import annotations
from typing import List
import logging

from dynamicprompts import constants
from . import PromptGenerator

logger = logging.getLogger(__name__)


class BatchedCombinatorialPromptGenerator(PromptGenerator):
    def __init__(self, generator: PromptGenerator, batches=1):
        self._generator = generator
        self._batches = batches

    def generate(self, template, max_prompts=constants.MAX_IMAGES) -> List[str]:
        images = []

        for _ in range(self._batches):
            images.extend(self._generator.generate(template, max_prompts))
        return images
