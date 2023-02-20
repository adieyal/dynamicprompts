from dataclasses import dataclass


@dataclass(frozen=True)
class ParserConfig:
    variant_start: str = "{"
    variant_end: str = "}"
    wildcard_wrap: str = "__"


default_parser_config = ParserConfig()
