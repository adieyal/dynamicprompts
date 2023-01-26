from __future__ import annotations

from dynamicprompts.generators.promptgenerator import PromptGenerator


class DummyGenerator(PromptGenerator):
    def generate(
        self,
        template: str,
        num_images: int = 1,
    ) -> list[str]:
        return num_images * [template]
