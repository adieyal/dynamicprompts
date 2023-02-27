from __future__ import annotations

from unittest import mock

from dynamicprompts.commands import Command
from dynamicprompts.samplers import RandomSampler


def patch_random_sampler_variant_choices(random_choices: list[list[Command]]):
    """
    Return a mock.patch.object context manager that RandomSampler to return
    the given sequence of command sequences for variant commands.
    """
    # Guard against misuse of this utility
    assert isinstance(random_choices, list)
    assert all(isinstance(choices, list) for choices in random_choices)
    assert all(
        isinstance(choice, Command) for choices in random_choices for choice in choices
    )
    # Good to go
    return mock.patch.object(
        RandomSampler,
        "_get_variant_choices",
        side_effect=random_choices,
    )
