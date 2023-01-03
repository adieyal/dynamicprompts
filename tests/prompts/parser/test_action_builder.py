from unittest import mock

import pytest
 
from dynamicprompts.parser.action_builder import ActionBuilder
from dynamicprompts.parser.commands import LiteralCommand, WildcardCommand, VariantCommand, SequenceCommand

@pytest.fixture
def wildcard_manager():
    return mock.Mock()

@pytest.fixture
def action_builder(wildcard_manager):
    return ActionBuilder(wildcard_manager)

class TestActionBuilder:
    def test_literal_action(self, action_builder: ActionBuilder):
        literal_action = action_builder.get_literal_action("test")
        assert isinstance(literal_action, LiteralCommand)
        assert literal_action.literal == "test"

    def test_literal_action_with_array(self, action_builder: ActionBuilder):
        prompt = "This is a test"
        literal_action = action_builder.get_literal_action(prompt.split())
        assert isinstance(literal_action, LiteralCommand)
        assert literal_action.literal == prompt

    def test_wildcard_action(self, action_builder: ActionBuilder):
        prompt = "__wildcard__"
        wildcard_action = action_builder.get_wildcard_action(prompt)
        assert isinstance(wildcard_action, WildcardCommand)
        assert wildcard_action.wildcard == prompt

    # def test_variant_action(self, action_builder: ActionBuilder):
    #     prompt = "{A|B|C}"
    #     variant_action = action_builder.get_variant_action(prompt)
    #     assert isinstance(variant_action, VariantCommand)

    def test_sequence_action(self, action_builder: ActionBuilder):
        commands = [LiteralCommand("A"), LiteralCommand("string"), LiteralCommand("of"), LiteralCommand("tokens")]
        sequence = action_builder.get_sequence_action(commands)
        assert isinstance(sequence, SequenceCommand)
        assert len(sequence) == 4

        for idx, command in enumerate(commands):
            assert sequence[idx] == command