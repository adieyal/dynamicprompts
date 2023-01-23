from __future__ import annotations

from abc import ABC, abstractmethod


class PromptGenerator(ABC):
    @abstractmethod
    def generate(self, *args, **kwargs) -> list[str]:
        pass


class GeneratorException(Exception):
    pass
