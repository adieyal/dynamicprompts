from __future__ import annotations
from typing import List

from .promptgenerator import PromptGenerator


class DummyGenerator(PromptGenerator):
    def generate(self, template, num_images) -> List[str]:
        return num_images * [template]
