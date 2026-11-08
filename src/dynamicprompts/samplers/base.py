from __future__ import annotations

import logging
from itertools import islice

from dynamicprompts.commands import (
    Command,
    LiteralCommand,
    SequenceCommand,
    VariantCommand,
    WildcardCommand,
    WrapCommand,
)
from dynamicprompts.commands.variable_commands import (
    VariableAccessCommand,
    VariableAssignmentCommand,
)
from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.sampling_result import SamplingResult
from dynamicprompts.types import ResultGen, to_result_gen
from dynamicprompts.utils import rotate_and_join

logger = logging.getLogger(__name__)


def _is_sampled_immediate_assignment(command: Command) -> bool:
    # Literal values need no sampling (see process_variable_assignment).
    return (
        isinstance(command, VariableAssignmentCommand)
        and command.immediate
        and not isinstance(command.value, LiteralCommand)
    )


def _may_read_variables(command: Command) -> bool:
    if isinstance(command, LiteralCommand):
        return False
    if isinstance(command, SequenceCommand):
        return any(_may_read_variables(c) for c in command.tokens)
    if isinstance(command, VariantCommand):
        return any(_may_read_variables(c) for c in command.values)
    # Variable accesses, and wildcards, whose files may reference variables.
    return True


def resolve_variable(
    command: VariableAccessCommand,
    context: SamplingContext,
) -> Command:
    """
    The command a variable access samples: its value, else its default,
    else the context's unknown_variable_value. Raises KeyError if there is none.
    """
    variable = command.name
    command_to_sample = context.variables.get(variable, command.default)
    if not command_to_sample:
        if context.unknown_variable_value is None:
            raise KeyError(f"Variable {variable} is not defined in this context")
        elif isinstance(context.unknown_variable_value, str):
            command_to_sample = LiteralCommand(context.unknown_variable_value)
        else:
            command_to_sample = context.unknown_variable_value
    return command_to_sample


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
        if isinstance(command, WrapCommand):
            return self._get_wrap(command, context)
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
        if not any(_is_sampled_immediate_assignment(c) for c in command.tokens):
            tokens, context = context.process_variable_assignments(command.tokens)
            sub_generators = [context.generator_from_command(c) for c in tokens]

            while True:
                yield rotate_and_join(sub_generators, separator=command.separator)

        # Immediate assignments are evaluated once per prompt (#96).
        # Generators are kept across prompts so stateful samplers (cyclical)
        # don't restart: a command that can't read variables keeps one generator,
        # one that can gets one generator per set of immediate values.
        generators: dict[tuple[int, tuple[str, ...]], ResultGen] = {}

        def get_generator(
            index: int,
            sub_command: Command,
            sub_context: SamplingContext,
            values: tuple[str, ...],
        ) -> ResultGen:
            key = (index, values if _may_read_variables(sub_command) else ())
            if key not in generators:
                generators[key] = sub_context.generator_from_command(sub_command)
            return generators[key]

        while True:
            prompt_context = context
            values: tuple[str, ...] = ()
            for index, token in enumerate(command.tokens):
                if not isinstance(token, VariableAssignmentCommand):
                    continue
                if _is_sampled_immediate_assignment(token) and (
                    token.overwrite or token.name not in prompt_context.variables
                ):
                    value_gen = get_generator(
                        index,
                        token.value,
                        prompt_context,
                        values,
                    )
                    value = str(next(value_gen))
                    values += (value,)
                    prompt_context = prompt_context.with_variables(
                        {token.name: LiteralCommand(value)},
                    )
                else:
                    prompt_context = prompt_context.with_variables(
                        {token.name: prompt_context.process_variable_assignment(token)},
                    )
            sub_generators = [
                get_generator(index, token, prompt_context, values)
                for index, token in enumerate(command.tokens)
                if not isinstance(token, VariableAssignmentCommand)
            ]
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
        command_to_sample = resolve_variable(command, context)
        gen = context.for_sampling_variable(command.name).generator_from_command(
            command_to_sample,
        )
        if context.yields_once(command_to_sample):
            return to_result_gen(islice(gen, 1))
        return gen

    def _get_wrap(
        self,
        command: WrapCommand,
        context: SamplingContext,
    ) -> ResultGen:
        return self._unsupported_command(command)
