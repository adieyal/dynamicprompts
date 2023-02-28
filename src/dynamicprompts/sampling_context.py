from __future__ import annotations

import dataclasses
import warnings
from itertools import islice
from random import Random
from typing import TYPE_CHECKING, Iterable

from dynamicprompts.commands import Command
from dynamicprompts.constants import DEFAULT_RANDOM
from dynamicprompts.enums import SamplingMethod
from dynamicprompts.parser.config import ParserConfig, default_parser_config
from dynamicprompts.types import StringGen
from dynamicprompts.utils import squash_whitespace
from dynamicprompts.wildcardmanager import WildcardManager

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

    def generator_from_command(self, command: Command) -> StringGen:
        samp, ctx = self.get_sampler_and_context(command)
        return samp.generator_from_command(command, ctx)

    def sample_prompts(
        self,
        prompt: str | Command,
        num_prompts: int | None = None,
    ) -> Iterable[str]:
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
            gen = (squash_whitespace(p) for p in gen)

        if num_prompts is None:
            return gen
        return islice(gen, num_prompts)

    def get_effective_sampling_method(self, command: Command) -> SamplingMethod:
        if command.sampling_method:
            return command.sampling_method
        return self.default_sampling_method
