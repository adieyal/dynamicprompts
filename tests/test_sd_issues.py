"""
Tests for issues reported on the downstream sd-dynamic-prompts repo.
"""

import pytest
from dynamicprompts.commands import SequenceCommand, VariantCommand
from dynamicprompts.generators import (
    CombinatorialPromptGenerator,
    RandomPromptGenerator,
)
from dynamicprompts.parser.parse import parse
from dynamicprompts.wildcards import WildcardManager
from dynamicprompts.wildcards.collection.list import ListWildcardCollection
from dynamicprompts.wildcards.collection.structured import _parse_structured_file_list


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


def test_sd_237(wildcard_manager: WildcardManager):
    """Similar to #223. Fixed by #23."""
    prompt = "{2$$ 1| 2| 3} {2$$ 1| 2| 3}"

    parsed = parse(prompt)
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
    parsed = parse("prompt with closing bra}ce but {parsed|accepted}")
    assert isinstance(parsed, SequenceCommand)
    lit1, variant1 = parsed
    assert lit1.literal == "prompt with closing bra}ce but "
    assert len(variant1.values) == 2


def test_sd_307(wildcard_manager: WildcardManager):
    generator = RandomPromptGenerator(wildcard_manager)
    prompts = generator.generate("{2$$__colors-cold__}", 2)
    colors = wildcard_manager.get_values("colors-cold")
    combinations = [f"{c1},{c2}" for c1 in colors for c2 in colors if c1 != c2]
    # check the every prompt is a combination of two colors
    assert all(p in combinations for p in prompts)


def test_sd_324():
    generator = RandomPromptGenerator(ignore_whitespace=True)
    s = """{
        # 60% A
        0.6::A
        |
        # 40% B
        0.4::B
        }
        """

    prompts = generator.generate(s, 10)

    assert all(p in ["A", "B"] for p in prompts)


def test_dp_28():
    generator = RandomPromptGenerator(ignore_whitespace=True)
    s = "{1$$A|B|{2$$ and $$X|Y|Z}}"
    prompts = generator.generate(s, 10)

    assert len(prompts) == 10
    expected = {
        "A",
        "B",
        "X and Y",
        "X and Z",
        "Y and X",
        "Y and Z",
        "Z and X",
        "Z and Y",
    }
    assert all(str(p) in expected for p in prompts)


def test_sd_358(wildcard_manager: WildcardManager):
    generator = RandomPromptGenerator(wildcard_manager)
    prompts = generator.generate("{2$$__referencing-colors__}", 2)
    colors = wildcard_manager.get_values(
        "colors-cold",
    ) + wildcard_manager.get_values("colors-warm")
    combinations = [f"{c1},{c2}" for c1 in colors for c2 in colors if c1 != c2]
    # check the every prompt is a combination of two colors
    assert all(str(p) in combinations for p in prompts)


def test_sd_377(wildcard_manager: WildcardManager, caplog):
    """
    Test that references to other wildcards within wildcard files
    are fallback-resolved to anywhere in the wildcard hierarchy.
    """
    if wildcard_manager.wildcard_wrap != "__":
        pytest.skip("This test requires the __ wildcard wrap")
    cpg = CombinatorialPromptGenerator(wildcard_manager)
    generated = set(
        cpg.generate(wildcard_manager.to_wildcard("animals/all-references")),
    )
    assert generated == {"dog", "wolf", "cat", "tiger", "unicorn"}
    # We should get log messages
    assert any(r.message.startswith("No matches for wildcard") for r in caplog.records)


def test_sd_665():
    # https://github.com/adieyal/sd-dynamic-prompts/issues/665

    expr = "{3::|looking up view|looking down view|birds-eye view}"
    wi = list(_parse_structured_file_list([expr]))
    assert len(wi) == 1
    assert wi[0] == expr


def test_sd_672(wildcard_manager: WildcardManager):
    # https://github.com/adieyal/sd-dynamic-prompts/discussions/672

    tpl = "{|hot,}{|summer,}{|blue sky,}"
    generator = CombinatorialPromptGenerator(wildcard_manager)
    assert any("," in prompt for prompt in generator.generate(tpl))


def test_sd_572(caplog):
    """
    Test that we don't crash if a wildcard collection we're expanding has
    values that can't be parsed as wildcards.
    """
    wildcard_manager = WildcardManager.from_map(
        {
            "x": ListWildcardCollection(["{", "__", "}"]),
        },
    )
    tpl = "{3$$__*__}"
    generator = CombinatorialPromptGenerator(wildcard_manager)
    prompts = set(generator.generate(tpl))
    # Prompts will get generated...
    assert prompts == {"__,{,}", "__,},{", "{,__,}", "{,},__", "},__,{", "},{,__"}
    # Check we emitted some warnings as we went
    assert ("Expected end of text" in r.message for r in caplog.records)
