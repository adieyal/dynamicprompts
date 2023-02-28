import pytest
from dynamicprompts.commands import LiteralCommand, SequenceCommand
from dynamicprompts.enums import SamplingMethod
from dynamicprompts.samplers.command_collection import CommandCollection
from dynamicprompts.types import CommandList


@pytest.fixture
def commands() -> CommandList:
    sequence_command = SequenceCommand.from_literals(["a", "b", "c"])
    return sequence_command.tokens


class TestCommandCollection:
    def test_empty_collection(self, combinatorial_sampling_context):
        collection = CommandCollection([], combinatorial_sampling_context)
        assert len(collection.commands) == 0
        assert len(collection.generators) == 0

    def test_generators_created(
        self,
        commands: CommandList,
        random_sampling_context,
    ):
        collection = CommandCollection(commands, context=random_sampling_context)
        assert len(collection.commands) == 3
        assert len(collection.generators) == 3

        assert collection.commands[0].literal == "a"
        assert collection.commands[1].literal == "b"
        assert collection.commands[2].literal == "c"

        for command, generator in zip(commands, collection.generators):
            assert next(generator) == command.literal

        generator = collection.generators[0]
        assert next(generator) == "a"
        assert next(generator) == "a"
        assert next(generator) == "a"
        assert next(generator) == "a"

    def test_generators_values(self, commands, combinatorial_sampling_context):
        collection = CommandCollection(commands, combinatorial_sampling_context)

        for command in commands:
            assert collection.get_value(command) == command.literal

    def test_generators_for_missing_command(
        self,
        commands,
        combinatorial_sampling_context,
    ):
        collection = CommandCollection(commands, combinatorial_sampling_context)
        missing_command = LiteralCommand("missing")

        with pytest.raises(ValueError):
            collection.get_value(missing_command)

    def test_with_finite_sampling_method(
        self,
        commands,
        combinatorial_sampling_context,
    ):
        combinatorial_command = LiteralCommand(
            "combinatorial",
            sampling_method=SamplingMethod.COMBINATORIAL,
        )
        collection = CommandCollection(
            commands + [combinatorial_command],
            combinatorial_sampling_context,
        )

        assert collection.get_value(combinatorial_command) == "combinatorial"
        assert collection.get_value(combinatorial_command) is None
