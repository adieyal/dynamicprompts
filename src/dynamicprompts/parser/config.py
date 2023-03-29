from dataclasses import dataclass


@dataclass(frozen=True)
class ParserConfig:
    variant_start: str = "{"
    variant_end: str = "}"
    wildcard_wrap: str = "__"
    variable_start: str = "${"
    variable_end: str = "}"


default_parser_config = ParserConfig()
