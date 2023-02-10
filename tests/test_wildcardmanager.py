from pathlib import Path

import pytest
from dynamicprompts.wildcardmanager import WildcardManager, _clean_wildcard

from tests.conftest import WILDCARD_DATA_DIR


def test_path(wildcard_manager: WildcardManager):
    assert wildcard_manager.path == WILDCARD_DATA_DIR


def test_is_wildcard(wildcard_manager: WildcardManager):
    assert wildcard_manager.is_wildcard("__test__")
    assert not wildcard_manager.is_wildcard("test")


def test_get_all_values(wildcard_manager: WildcardManager):
    assert wildcard_manager.get_all_values("color*") == [
        "blue",
        "green",
        "red",
        "yellow",
    ]
    assert wildcard_manager.get_all_values("flavors/*") == [
        "chocolate",
        "grapefruit",
        "lemon",
        "strawberry",
        "vanilla",
    ]


def test_match_files_with_missing_wildcard(wildcard_manager: WildcardManager):
    assert wildcard_manager.match_files("__invalid_wildcard__") == []


def test_get_all_values_with_missing_wildcard(wildcard_manager: WildcardManager):
    assert wildcard_manager.get_all_values("__invalid_wildcard__") == []


def test_collections(wildcard_manager: WildcardManager):
    assert wildcard_manager.get_collections() == ["derp"]


def test_hierarchy(wildcard_manager: WildcardManager):
    assert wildcard_manager.get_wildcard_hierarchy() == (
        ["__colors-cold__", "__colors-warm__", "__variant__"],  # Top level
        {  # child folders
            "animals": (
                ["__animals/mystical__"],
                {
                    "mammals": (
                        ["__animals/mammals/canine__", "__animals/mammals/feline__"],
                        {},
                    ),
                },
            ),
            "flavors": (
                ["__flavors/sour__", "__flavors/sweet__"],
                {},
            ),
        },
    )


def test_backslash_norm(wildcard_manager: WildcardManager):
    assert len(wildcard_manager.get_all_values("flavors\\*")) == 5
    # Empirically, this also works on Windows


def test_directory_traversal(wildcard_manager: WildcardManager):
    assert not wildcard_manager.get_all_values("../cant_touch_this")
    assert not wildcard_manager.get_all_values("..\\cant_touch_this")


def test_clean_wildcard():
    with pytest.raises(ValueError):
        _clean_wildcard("/foo")

    with pytest.raises(ValueError):
        _clean_wildcard("\\foo")

    with pytest.raises(ValueError):
        _clean_wildcard("foo/../bar")


def test_wildcard_symlinks(tmp_path: Path):
    internet_animals = {"doggo", "catto", "otto"}
    cool_animals = {"cool bear", "cool penguin"}
    wild_things = {"plants", "forest", "flowers", "sunshine"}

    # Prepare a file outside the wildcard directory
    # that we'll have a symlink point to.
    # We will be able to read this file via the symlink.
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    secret_file = outside_dir / "wilderness.txt"
    secret_file.write_text("\n".join(wild_things))

    # Prepare the wildcard directory with real files...
    wildcards_dir = tmp_path / "wildcards"
    animals_dir = wildcards_dir / "animals"
    animals_dir.mkdir(parents=True)
    internet_animals_file = animals_dir / "internet.txt"
    internet_animals_file.write_text("\n".join(internet_animals))
    cool_animals_file = animals_dir / "cool.txt"
    cool_animals_file.write_text("\n".join(cool_animals))

    # Prepare symlinks.
    friendos_file = wildcards_dir / "friendos.txt"
    friendos_file.symlink_to(internet_animals_file)
    polar_file = wildcards_dir / "wow_polar.txt"
    polar_file.symlink_to(cool_animals_file.relative_to(polar_file.parent))
    wild_file = wildcards_dir / "wild.txt"
    wild_file.symlink_to(secret_file)

    wcm = WildcardManager(wildcards_dir)
    assert {w.name for w in wcm.match_files("*")} == {
        "animals/cool",
        "animals/internet",
        "friendos",
        "wild",
        "wow_polar",
    }

    # Check that regular and symlinked files are available.
    assert (
        set(wcm.get_all_values("animals/internet"))
        == set(wcm.get_all_values("friendos"))
        == internet_animals
    )

    # Wilderness available via symlink?
    assert set(wcm.get_all_values("wild")) == wild_things
    # ... No directory traversal though!
    assert not wcm.get_all_values("../outside/wilderness")

    # Now, let's get extra wild and symlink an entire directory...
    wildly_dir = wildcards_dir / "wildly"
    wildly_dir.symlink_to(outside_dir)
    # ... and write some more there!
    wilder_file = wildly_dir / "wilder.txt"
    wilder_file.write_text("whoa!!!")
    assert set(wcm.get_all_values("wildly/*")) == {
        *wild_things,
        "whoa!!!",
    }
