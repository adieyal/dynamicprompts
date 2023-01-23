from __future__ import annotations

from dynamicprompts.generators.promptgenerator import PromptGenerator


class DummyGenerator(PromptGenerator):
    def generate(self, template, num_images=1) -> list[str]:
        return num_images * [template]
