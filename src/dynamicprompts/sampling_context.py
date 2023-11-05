from __future__ import annotations

import dataclasses
import warnings
from itertools import islice
from random import Random
from typing import TYPE_CHECKING, Iterable

from dynamicprompts.commands import Command, LiteralCommand
from dynamicprompts.commands.variable_commands import VariableAssignmentCommand
from dynamicprompts.constants import DEFAULT_RANDOM
from dynamicprompts.enums import SamplingMethod
from dynamicprompts.parser.config import ParserConfig, default_parser_config
from dynamicprompts.sampling_result import SamplingResult
from dynamicprompts.types import ResultGen
from dynamicprompts.wildcards import WildcardManager

if TYPE_CHECKING:
    from dynamicprompts.samplers import Sampler


def _build_default_samplers():
    from dynamicprompts.samplers.combinatorial import CombinatorialSampler
    from dynamicprompts.samplers.cycle import CyclicalSampler
    from dynamicprompts.samplers.random import RandomSampler

    return {
        SamplingMethod.COMBINATORIAL: CombinatorialSampler(),
        SamplingMethod.CYCLICAL: CyclicalSampler(),
        SamplingMethod.RANDOM: RandomSampler(),
    }


@dataclasses.dataclass(frozen=True)
class SamplingContext:
    default_sampling_method: SamplingMethod
    wildcard_manager: WildcardManager
    samplers: dict[SamplingMethod, Sampler] = dataclasses.field(
        default_factory=_build_default_samplers,
    )
    ignore_whitespace: bool = False
    parser_config: ParserConfig = default_parser_config
    rand: Random = DEFAULT_RANDOM
    variables: dict[str, Command] = dataclasses.field(default_factory=dict)

    # Value for variables that aren't defined in the present context.
    # None will raise an error.
    unknown_variable_value: str | Command | None = None

    # Variables that are currently sampled, to prevent infinite recursion
    _variables_being_sampled: set[str] = dataclasses.field(default_factory=set)

    def with_sampling_method(self, sampling_method: SamplingMethod) -> SamplingContext:
        return dataclasses.replace(self, default_sampling_method=sampling_method)

    @property
    def default_sampler(self) -> Sampler:
        return self.samplers[self.default_sampling_method]

    def get_sampler_and_context(
        self,
        command: Command,
    ) -> tuple[Sampler, SamplingContext]:
        """
        Get the correct sampler instance and a sub-context (if necessary) for the given command.
        """
        new_sampling_method = command.sampling_method or self.default_sampling_method
        if new_sampling_method != self.default_sampling_method:
            if self.default_sampling_method.is_nonfinite():  # Within non-finite context
                if not new_sampling_method.is_nonfinite():
                    # ...but using finite method?
                    warnings.warn(
                        f"Command {command} has finite sampling method {new_sampling_method} "
                        f"that can't be nested within this non-finite context {self.default_sampling_method}, "
                        f"so using {self.default_sampling_method} instead.",
                    )
                    new_sampling_method = self.default_sampling_method
            sampler = self.samplers[new_sampling_method]
            context = self.with_sampling_method(new_sampling_method)
        else:
            sampler = self.samplers[self.default_sampling_method]
            context = self
        return sampler, context

    def with_variables(self, variables: dict[str, Command]) -> SamplingContext:
        if not variables:  # Nothing to replace
            return self
        return dataclasses.replace(self, variables={**self.variables, **variables})

    def for_sampling_variable(self, variable: str) -> SamplingContext:
        if variable in self._variables_being_sampled:
            raise RecursionError(f"Variable {variable} is being sampled recursively")
        return dataclasses.replace(
            self,
            _variables_being_sampled=self._variables_being_sampled | {variable},
        )

    def generator_from_command(self, command: Command) -> ResultGen:
        samp, ctx = self.get_sampler_and_context(command)
        return samp.generator_from_command(command, ctx)

    def sample_prompts(
        self,
        prompt: str | Command,
        num_prompts: int | None = None,
    ) -> Iterable[SamplingResult]:
        """
        Generate prompts from a prompt template.

        :param prompt: The prompt template to generate prompts from.
        :param num_prompts: How many prompts to generate (at most). If None, generate all possible prompts.
        """
        if not prompt:
            return []
        command: Command
        if isinstance(prompt, str):
            from dynamicprompts.parser.parse import parse

            command = parse(prompt, parser_config=self.parser_config)
        elif isinstance(prompt, Command):
            command = prompt
        else:
            raise TypeError(f"Expected prompt to be str or Command, got {type(prompt)}")

        gen = self.generator_from_command(command)

        if self.ignore_whitespace:
            gen = (res.whitespace_squashed() for res in gen)

        if num_prompts is None:
            return gen
        return islice(gen, num_prompts)

    def get_effective_sampling_method(self, command: Command) -> SamplingMethod:
        if command.sampling_method:
            return command.sampling_method
        return self.default_sampling_method

    def process_variable_assignments(
        self,
        commands: Iterable[Command],
    ) -> tuple[list[Command], SamplingContext]:
        """
        Evaluate any variable assignments in the given commands,
        and return the resulting commands and augmented context.

        If there are no variable assignments,
        the original commands and context are returned as-is.
        """
        new_variables: dict[str, Command] = {}
        new_commands = []
        for command in commands:
            if isinstance(command, VariableAssignmentCommand):
                new_variables[command.name] = self.process_variable_assignment(command)
            else:
                new_commands.append(command)
        if new_variables:
            return new_commands, self.with_variables(new_variables)
        return (new_commands, self)

    def process_variable_assignment(
        self,
        command: VariableAssignmentCommand,
    ) -> Command:
        if command.immediate:
            if isinstance(command.value, LiteralCommand):
                # Optimization: if the variable assignment is a literal, just use that
                return command.value
            # Sample the variable assignment command to get the value
            return LiteralCommand(
                str(
                    next(self.generator_from_command(command.value)),
                ),  # TODO: sus str cast from result?
            )
        return command.value
