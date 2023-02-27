from __future__ import annotations

from unittest.mock import patch

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
    return patch.object(
        RandomSampler,
        "_get_variant_choices",
        side_effect=random_choices,
    )


def patch_random_sampler_variant_num_choices(num_choices: list[int]):
    """
    Return a mock.patch.object context manager that RandomSampler to return
    the given sequence of num_choices for variant commands.
    """
    # Guard against misuse of this utility
    assert isinstance(num_choices, list)
    assert all(isinstance(num, int) for num in num_choices)
    # Good to go
    return patch.object(
        RandomSampler,
        "_get_variant_num_choices",
        side_effect=num_choices,
    )


def patch_random_sampler_wildcard_choice(choices: list[str]):
    """
    Return a mock.patch.object context manager that RandomSampler to return
    the given sequence of wildcard choices.
    """
    # Guard against misuse of this utility
    assert isinstance(choices, list)
    assert all(isinstance(choice, str) for choice in choices)
    # Good to go
    return patch.object(
        RandomSampler,
        "_get_wildcard_choice",
        side_effect=choices,
    )
