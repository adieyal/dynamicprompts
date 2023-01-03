from __future__ import annotations

from .promptgenerator import PromptGenerator


class DummyGenerator(PromptGenerator):
    def generate(self, template, num_images) -> list[str]:
        return num_images * [template]
