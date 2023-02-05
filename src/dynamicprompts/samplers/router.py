from __future__ import annotations

import typing
from itertools import islice

from dynamicprompts.commands.base import Command, SamplingMethod
from dynamicprompts.parser.parse import parse
from dynamicprompts.samplers.base import Sampler, SamplerRouter
from dynamicprompts.samplers.combinatorial import CombinatorialSampler
from dynamicprompts.samplers.cycle import CyclicalSampler
from dynamicprompts.samplers.random import RandomSampler
from dynamicprompts.types import StringGen
from dynamicprompts.utils import squash_whitespace
from dynamicprompts.wildcardmanager import WildcardManager


class ConcreteSamplerRouter(SamplerRouter):
    def __init__(
        self,
        *,
        wildcard_manager: WildcardManager,
        default_sampling_method: SamplingMethod,
        ignore_whitespace=False,
    ):
        if default_sampling_method == SamplingMethod.DEFAULT:
            raise ValueError("Cannot use default sampling method for generic sampler.")

        self._wildcard_manager = wildcard_manager
        self._ignore_whitespace = ignore_whitespace

        kwargs = {
            "wildcard_manager": wildcard_manager,
            "ignore_whitespace": ignore_whitespace,
            "sampler_manager": self,
        }

        random_sampler = RandomSampler(**kwargs)
        combinatorial_sampler = CombinatorialSampler(**kwargs)
        cyclical_sampler = CyclicalSampler(**kwargs)

        default_sampler = {
            SamplingMethod.RANDOM: random_sampler,
            SamplingMethod.COMBINATORIAL: combinatorial_sampler,
            SamplingMethod.CYCLICAL: cyclical_sampler,
        }.get(default_sampling_method)

        if default_sampler is None:
            raise ValueError(
                f"Invalid default sampling method: {default_sampling_method}",
            )

        self._samplers: dict[SamplingMethod, Sampler] = {
            SamplingMethod.RANDOM: random_sampler,
            SamplingMethod.COMBINATORIAL: combinatorial_sampler,
            SamplingMethod.CYCLICAL: cyclical_sampler,
            SamplingMethod.DEFAULT: default_sampler,
        }

    def generator_from_command(self, command) -> StringGen:
        return self._samplers[command.sampling_method].generator_from_command(command)

    def sample_prompts(
        self,
        prompt: str | Command,
        num_prompts: int | None = None,
    ) -> typing.Iterable[str]:
        """
        Generate prompts from a prompt template.

        :param prompt: The prompt template to generate prompts from.
        :param num_prompts: How many prompts to generate (at most). If None, generate all possible prompts.
        """
        if not prompt:
            return []
        command: Command
        if isinstance(prompt, str):
            command = parse(prompt)
        elif isinstance(prompt, Command):
            command = prompt
        else:
            raise TypeError(f"Expected prompt to be str or Command, got {type(prompt)}")
        gen = self.generator_from_command(command)

        if self._ignore_whitespace:
            gen = (squash_whitespace(p) for p in gen)

        if num_prompts is None:
            return gen
        return islice(gen, num_prompts)
