from dataclasses import dataclass


@dataclass
class ParserConfig:
    left_brace: str = "{"
    right_brace: str = "}"


default_parser_config = ParserConfig()
