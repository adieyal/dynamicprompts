from __future__ import annotations

from functools import partial
from pathlib import Path

import pytest
from dynamicprompts.wildcards import WildcardManager
from dynamicprompts.wildcards.collection import WildcardTextFile
from dynamicprompts.wildcards.utils import clean_wildcard

from tests.conftest import WILDCARD_DATA_DIR


def test_pathless_wm():
    wm = WildcardManager()
    assert not wm.path
    assert not wm.get_all_values("test")
    assert not list(wm.match_collections("test"))


def test_path(wildcard_manager: WildcardManager):
    assert wildcard_manager.path == WILDCARD_DATA_DIR


def test_is_wildcard(wildcard_manager: WildcardManager):
    ww = wildcard_manager.wildcard_wrap
    assert wildcard_manager.is_wildcard(f"{ww}test{ww}")
    assert not wildcard_manager.is_wildcard("test")


def test_get_all_values(wildcard_manager: WildcardManager):
    assert wildcard_manager.get_all_values("color*") == [
        "blue",
        "green",
        "red",
        "yellow",
    ]
    assert wildcard_manager.get_all_values("flavors/*") == [
        "chocolate",  # sweet
        "coffee",  # bitter (from pantry JSON)
        "dark chocolate",  # bitter (from pantry JSON)
        "grapefruit",  # sour
        "lemon",  # sour
        "strawberry",  # sweet
        "vanilla",  # sweet
    ]


def test_pantry_expansion(wildcard_manager: WildcardManager):
    """
    Test that a pantry file appears as if it was a wildcard file.
    """
    assert wildcard_manager.get_all_values("flavors/bitter") == [
        "coffee",
        "dark chocolate",
    ]
    assert wildcard_manager.get_all_values("clothing") == ["Pants", "Shoes", "T-shirt"]
    assert "Akseli Gallen-Kallela" in wildcard_manager.get_all_values("artists/finnish")


def test_match_files_with_missing_wildcard(wildcard_manager: WildcardManager):
    assert list(wildcard_manager.match_collections("__invalid_wildcard__")) == []


def test_get_all_values_with_missing_wildcard(wildcard_manager: WildcardManager):
    assert wildcard_manager.get_all_values("__invalid_wildcard__") == []


def test_hierarchy(wildcard_manager: WildcardManager):
    root = wildcard_manager.tree.root
    assert len(list(root.walk_items())) == 15
    assert set(root.collections) == {
        "clothing",  # from pantry YAML
        "colors-cold",  # .txt
        "colors-warm",  # .txt
        "referencing-colors",  # .txt
        "shapes",  # flat list YAML
        "variant",  # .txt
    }
    assert set(root.child_nodes["animals"].collections) == {"mystical"}
    assert set(root.child_nodes["animals"].child_nodes["mammals"].collections) == {
        "canine",
        "feline",
    }
    assert set(root.child_nodes["animals"].walk_full_names()) == {
        "animals/mammals/canine",
        "animals/mammals/feline",
        "animals/mystical",
    }
    assert set(root.child_nodes["flavors"].collections) == {
        "sour",  # .txt
        "sweet",  # .txt
        "bitter",  # from .json
    }
    assert set(root.child_nodes["artists"].collections) == {
        "finnish",  # from root pantry YAML's nested dict
        "dutch",  # from root pantry YAML's nested dict
    }


def test_backslash_norm(wildcard_manager: WildcardManager):
    assert len(wildcard_manager.get_all_values("flavors\\*")) == 7
    # Empirically, this also works on Windows


def test_directory_traversal(wildcard_manager: WildcardManager):
    assert not wildcard_manager.get_all_values("../cant_touch_this")
    assert not wildcard_manager.get_all_values("..\\cant_touch_this")


def test_clean_wildcard(wildcard_manager: WildcardManager):
    clean = partial(clean_wildcard, wildcard_wrap=wildcard_manager.wildcard_wrap)
    with pytest.raises(ValueError):
        clean("/foo")

    with pytest.raises(ValueError):
        clean("\\foo")

    with pytest.raises(ValueError):
        clean("foo/../bar")

    ww = wildcard_manager.wildcard_wrap
    assert clean(f"{ww}foo{ww}", wildcard_wrap=ww) == "foo"


def test_to_wildcard(wildcard_manager: WildcardManager):
    ww = wildcard_manager.wildcard_wrap
    assert wildcard_manager.to_wildcard("foo") == f"{ww}foo{ww}"
    assert wildcard_manager.to_wildcard(f"{ww}foo{ww}") == f"{ww}foo{ww}"


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
    assert wcm.get_collection_names() == {
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
    wcm.clear_cache()
    assert set(wcm.get_all_values("wildly/*")) == {
        *wild_things,
        "whoa!!!",
    }


def test_read_write_is_idempotent(wildcard_manager: WildcardManager):
    wf = wildcard_manager.get_file("colors-cold")
    assert isinstance(wf, WildcardTextFile)
    orig_values = list(wf.get_values())
    assert list(wf.get_values()) == orig_values  # exercise the cache
    text = wf.read_text()
    wf.write_text(text)
    assert list(wf.get_values()) == orig_values
