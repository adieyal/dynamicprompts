from __future__ import annotations
from typing import List

from abc import ABC, abstractmethod

class PromptGenerator(ABC):
    @abstractmethod
    def generate(self, *args, **kwargs) -> List[str]:
        pass


class GeneratorException(Exception):
    pass