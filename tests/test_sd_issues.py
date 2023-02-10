"""
Tests for issues reported on the downstream sd-dynamic-prompts repo.
"""

from dynamicprompts.commands import SequenceCommand, VariantCommand
from dynamicprompts.parser.parse import default_parser_config, parse
from dynamicprompts.wildcardmanager import WildcardManager


def test_sd_223():
    """Test that separators aren't parsed too greedily. Fixed by #23."""
    prompt = """
prefix,
({0$$a|b} {1$$c|d|e}),
suffix
    """.strip()
    parsed = parse(prompt, parser_config=default_parser_config)
    assert isinstance(parsed, SequenceCommand)
    lit1, variant1, lit2, variant2, lit3 = parsed
    assert lit1.literal == "prefix,\n("
    assert lit2.literal == " "
    assert lit3.literal == "),\nsuffix"
    assert len(variant1.values) == 2
    assert variant1.min_bound == variant1.max_bound == 0
    assert len(variant2.values) == 3
    assert variant2.min_bound == variant2.max_bound == 1


def test_sd_237(wildcard_manager: WildcardManager):
    """Similar to #223. Fixed by #23."""
    prompt = "{2$$ 1| 2| 3} {2$$ 1| 2| 3}"

    parsed = parse(prompt, parser_config=default_parser_config)
    assert isinstance(parsed, SequenceCommand)
    variant1, lit1, variant2 = parsed

    assert lit1.literal == " "

    assert len(variant1.values) == 3
    assert variant1.min_bound == variant1.max_bound == 2
    assert variant1.separator == VariantCommand.separator

    assert len(variant2.values) == 3
    assert variant2.min_bound == variant2.max_bound == 2
    assert variant2.separator == VariantCommand.separator


def test_sd_212(wildcard_manager: WildcardManager):
    """Test that closing braces are allowed within literals. Fixed by #24."""
    parsed = parse(
        "prompt with closing bra}ce but {parsed|accepted}",
        parser_config=default_parser_config,
    )
    assert isinstance(parsed, SequenceCommand)
    lit1, variant1 = parsed
    assert lit1.literal == "prompt with closing bra}ce but "
    assert len(variant1.values) == 2
