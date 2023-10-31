from __future__ import annotations

import logging

from dynamicprompts.commands import (
    Command,
    LiteralCommand,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
)
from dynamicprompts.commands.variable_commands import (
    VariableAccessCommand,
    VariableAssignmentCommand,
)
from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.sampling_result import SamplingResult
from dynamicprompts.types import ResultGen
from dynamicprompts.utils import rotate_and_join

logger = logging.getLogger(__name__)


class Sampler:
    def generator_from_command(
        self,
        command: Command,
        context: SamplingContext,
    ) -> ResultGen:
        # This is purposely not a dict lookup/getattr magic thing, to make
        # it easier for code completion etc. to see what's going on.
        if isinstance(command, LiteralCommand):
            return self._get_literal(command, context)
        if isinstance(command, SequenceCommand):
            return self._get_sequence(command, context)
        if isinstance(command, VariantCommand):
            return self._get_variant(command, context)
        if isinstance(command, WildcardCommand):
            return self._get_wildcard(command, context)
        if isinstance(command, VariableAssignmentCommand):
            raise NotImplementedError(
                "VariableAssignmentCommand should never be sampled",
            )
        if isinstance(command, VariableAccessCommand):
            return self._get_variable(command, context)
        return self._unsupported_command(command)

    def _unsupported_command(self, command: Command) -> ResultGen:
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support {command.__class__.__name__}",
        )

    def _get_wildcard(
        self,
        command: WildcardCommand,
        context: SamplingContext,
    ) -> ResultGen:
        return self._unsupported_command(command)

    def _get_variant(
        self,
        command: VariantCommand,
        context: SamplingContext,
    ) -> ResultGen:
        return self._unsupported_command(command)

    def _get_sequence(
        self,
        command: SequenceCommand,
        context: SamplingContext,
    ) -> ResultGen:
        tokens, context = context.process_variable_assignments(command.tokens)
        sub_generators = [context.generator_from_command(c) for c in tokens]

        while True:
            yield rotate_and_join(sub_generators, separator=command.separator)

    def _get_literal(
        self,
        command: LiteralCommand,
        context: SamplingContext,
    ) -> ResultGen:
        while True:
            yield SamplingResult(text=command.literal)

    def _get_variable(
        self,
        command: VariableAccessCommand,
        context: SamplingContext,
    ) -> ResultGen:
        variable = command.name
        command_to_sample = context.variables.get(variable, command.default)
        if not command_to_sample:
            if context.unknown_variable_value is None:
                raise KeyError(f"Variable {variable} is not defined in this context")
            elif isinstance(context.unknown_variable_value, str):
                command_to_sample = LiteralCommand(context.unknown_variable_value)
            else:
                command_to_sample = context.unknown_variable_value
        return context.for_sampling_variable(variable).generator_from_command(
            command_to_sample,
        )
