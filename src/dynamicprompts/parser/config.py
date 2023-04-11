from dataclasses import dataclass


# NB: this class needs to remain `frozen`, because it's used
#     as a key for `get_cached_parser`'s weak-key dictionary.
@dataclass(frozen=True)
class ParserConfig:
    variant_start: str = "{"
    variant_end: str = "}"
    wildcard_wrap: str = "__"
    variable_start: str = "${"
    variable_end: str = "}"


default_parser_config = ParserConfig()
