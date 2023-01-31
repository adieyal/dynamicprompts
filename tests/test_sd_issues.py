"""
Tests for issues reported on the downstream sd-dynamic-prompts repo.
"""

from dynamicprompts.commands import SequenceCommand
from dynamicprompts.parser.parse import parse
from dynamicprompts.wildcardmanager import WildcardManager


def test_sd_223():
    """Test that separators aren't parsed too greedily. Fixed by #23."""
    prompt = """
prefix,
({0$$a|b} {1$$c|d|e}),
suffix
    """.strip()
    parsed = parse(prompt)
    assert isinstance(parsed, SequenceCommand)
    lit1, variant1, lit2, variant2, lit3 = parsed
    assert lit1.literal == "prefix,\n("
    assert lit2.literal == " "
    assert lit3.literal == "),\nsuffix"
    assert len(variant1.values) == 2
    assert variant1.min_bound == variant1.max_bound == 0
    assert len(variant2.values) == 3
    assert variant2.min_bound == variant2.max_bound == 1


def test_sd_212(wildcard_manager: WildcardManager):
    """Test that closing braces are allowed within literals. Fixed by #24."""
    parsed = parse("prompt with closing bra}ce but {parsed|accepted}")
    assert isinstance(parsed, SequenceCommand)
    lit1, variant1 = parsed
    assert lit1.literal == "prompt with closing bra}ce but "
    assert len(variant1.values) == 2
