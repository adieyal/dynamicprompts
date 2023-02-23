import pytest
from dynamicprompts.commands import LiteralCommand, SequenceCommand
from dynamicprompts.enums import SamplingMethod
from dynamicprompts.sampler_routers.concrete_sampler_router import ConcreteSamplerRouter
from dynamicprompts.samplers.base import SamplerRouter
from dynamicprompts.samplers.command_collection import CommandCollection
from dynamicprompts.types import CommandList


@pytest.fixture
def router(wildcard_manager) -> SamplerRouter:
    return ConcreteSamplerRouter(
        wildcard_manager=wildcard_manager,
        default_sampling_method=SamplingMethod.RANDOM,
    )


@pytest.fixture
def commands() -> CommandList:
    sequence_command = SequenceCommand.from_literals(
        ["a", "b", "c"],
        sampling_method=SamplingMethod.RANDOM,
    )
    return sequence_command.tokens


class TestCommandCollection:
    def test_empty_collection(self, router):
        collection = CommandCollection([], router)
        assert len(collection.commands) == 0
        assert len(collection.generators) == 0

    def test_generators_created(self, router: SamplerRouter, commands: CommandList):
        collection = CommandCollection(commands, router)
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

    def test_generators_values(self, router, commands):
        collection = CommandCollection(commands, router)

        for command in commands:
            assert collection.get_value(command) == command.literal

    def test_generators_for_missing_command(self, router, commands):
        collection = CommandCollection(commands, router)
        missing_command = LiteralCommand("missing")

        with pytest.raises(ValueError):
            collection.get_value(missing_command)

    def test_with_finite_sampling_method(self, router, commands):
        combinatorial_command = LiteralCommand(
            "combinatorial",
            sampling_method=SamplingMethod.COMBINATORIAL,
        )
        collection = CommandCollection(commands + [combinatorial_command], router)

        assert collection.get_value(combinatorial_command) == "combinatorial"
        assert collection.get_value(combinatorial_command) is None
