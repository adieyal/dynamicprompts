from __future__ import annotations
from typing import List

from dynamicprompts.generators.promptgenerator import PromptGenerator


class DummyGenerator(PromptGenerator):
    def generate(self, template, num_images=1) -> List[str]:
        return num_images * [template]
