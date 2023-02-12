from __future__ import annotations

import logging
from abc import ABCMeta, abstractmethod

from dynamicprompts.commands import Command, LiteralCommand, SequenceCommand
from dynamicprompts.parser.config import ParserConfig, default_parser_config
from dynamicprompts.sampler_routers.sampler_router import SamplerRouter
from dynamicprompts.types import StringGen
from dynamicprompts.utils import rotate_and_join
from dynamicprompts.wildcardmanager import WildcardManager

logger = logging.getLogger(__name__)


class Sampler(metaclass=ABCMeta):
    def __init__(
        self,
        *,
        wildcard_manager: WildcardManager,
        parser_config: ParserConfig = default_parser_config,
        ignore_whitespace: bool = False,
        sampler_router: SamplerRouter,
    ):
        self._wildcard_manager = wildcard_manager
        self._ignore_whitespace = ignore_whitespace
        self._sampler_router = sampler_router
        self._parser_config = parser_config

    @abstractmethod
    def generator_from_command(self, command: Command) -> StringGen:
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement generator_from_command",
        )

    def _get_sequence(self, command: SequenceCommand) -> StringGen:
        generate_from_command = self._sampler_router.generator_from_command
        sub_generators = [generate_from_command(c) for c in command.tokens]

        while True:
            yield rotate_and_join(sub_generators, separator=command.separator)

    def _get_literal(self, command: LiteralCommand):
        while True:
            yield command.literal
