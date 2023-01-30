from dynamicprompts.commands import SequenceCommand
from dynamicprompts.parser.action_builder import ActionBuilder
from dynamicprompts.parser.parse import Parser
from dynamicprompts.wildcardmanager import WildcardManager


def test_legacy(wildcard_manager: WildcardManager):
    action_builder = ActionBuilder(wildcard_manager)
    parser = Parser(builder=action_builder)
    res = parser.parse("foo {a|b|c|d}")
    assert isinstance(res, SequenceCommand)
    assert res[0].literal == "foo "
    assert len(res[1]) == 4
