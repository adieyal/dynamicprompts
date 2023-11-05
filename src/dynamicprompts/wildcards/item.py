from dataclasses import dataclass


@dataclass(frozen=True)
class WildcardItem:
    content: str
    weight: float = 1.0

    def __str__(self) -> str:
        # Will make comparing with strings easier
        return self.content
