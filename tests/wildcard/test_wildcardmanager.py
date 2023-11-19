from __future__ import annotations

import random
import string
from functools import partial
from pathlib import Path

import pytest
from dynamicprompts.wildcards import WildcardManager
from dynamicprompts.wildcards.collection import WildcardTextFile
from dynamicprompts.wildcards.collection.list import ListWildcardCollection
from dynamicprompts.wildcards.utils import clean_wildcard

from tests.conftest import WILDCARD_DATA_DIR


def random_wildcard(length):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(length))


def test_pathless_wm():
    wm = WildcardManager()
    assert not wm.path
    assert not wm.get_values("test")
    assert not list(wm.match_collections("test"))


def test_path(wildcard_manager: WildcardManager):
    assert wildcard_manager.path == WILDCARD_DATA_DIR


def test_is_wildcard(wildcard_manager: WildcardManager):
    ww = wildcard_manager.wildcard_wrap
    assert wildcard_manager.is_wildcard(f"{ww}test{ww}")
    assert not wildcard_manager.is_wildcard("test")


def test_get_all_values(wildcard_manager: WildcardManager):
    assert wildcard_manager.get_values("color*").string_values == [
        "blue",
        "green",
        "red",
        "yellow",
    ]
    assert wildcard_manager.get_values("flavors/*").string_values == [
        "chocolate",  # sweet
        "coffee",  # bitter (from pantry JSON)
        "dark chocolate",  # bitter (from pantry JSON)
        "grapefruit",  # sour
        "lemon",  # sour
        "strawberry",  # sweet
        "vanilla",  # sweet
    ]


@pytest.mark.parametrize(
    ("sort", "dedup", "expected"),
    [
        (True, True, ["blue", "green", "red", "yellow"]),
        (False, True, ["red", "green", "blue", "yellow"]),
        (True, False, ["blue", "green", "red", "red", "yellow"]),
        (False, False, ["red", "green", "red", "blue", "yellow"]),
    ],
)
def test_get_all_values_sorted_and_deduplicated(sort, dedup, expected):
    colors = ["red", "green", "red", "blue", "yellow"]

    wildcard_manager = WildcardManager(
        root_map={"": [{"colors": ListWildcardCollection(colors)}]},
    )

    wildcard_manager.sort_wildcards = sort
    wildcard_manager.dedup_wildcards = dedup
    assert wildcard_manager.get_values("colors*").string_values == expected


def test_get_all_values_shuffled():
    wildcards = [random_wildcard(5) for i in range(40)]

    wildcard_manager = WildcardManager(
        root_map={"": [{"test_wildcards": ListWildcardCollection(wildcards)}]},
    )
    wildcard_manager.sort_wildcards = False
    wildcard_manager.dedup_wildcards = False
    assert wildcard_manager.get_values("test_wildcards").string_values == wildcards
    wildcard_manager.shuffle_wildcards = False
    assert wildcard_manager.get_values("test_wildcards").string_values == wildcards

    wildcard_manager.shuffle_wildcards = True
    retrieved_wildcards = wildcard_manager.get_values(
        "test_wildcards",
    ).string_values
    assert set(retrieved_wildcards) == set(wildcards)
    assert retrieved_wildcards != wildcards


def test_pantry_expansion(wildcard_manager: WildcardManager):
    """
    Test that a pantry file appears as if it was a wildcard file.
    """
    assert wildcard_manager.get_values("flavors/bitter").string_values == [
        "coffee",
        "dark chocolate",
    ]
    assert wildcard_manager.get_values("clothing").string_values == [
        "Pants",
        "Shoes",
        "T-shirt",
    ]
    assert "Akseli Gallen-Kallela" in wildcard_manager.get_values("artists/finnish")


def test_match_files_with_missing_wildcard(wildcard_manager: WildcardManager):
    assert list(wildcard_manager.match_collections("__invalid_wildcard__")) == []


def test_get_all_values_with_missing_wildcard(wildcard_manager: WildcardManager):
    assert not wildcard_manager.get_values("__invalid_wildcard__")


def test_hierarchy(wildcard_manager: WildcardManager):
    root = wildcard_manager.tree.root
    assert {name for name, item in root.walk_items()} == {
        "dupes",
        "animal",
        "animals/all-references",
        "animals/mammals/canine",
        "animals/mammals/feline",
        "animals/mystical",
        "animals/reptiles/lizards",
        "animals/reptiles/snakes",
        "artists/dutch",
        "artists/finnish",
        "clothing",
        "colors-cold",
        "colors-warm",
        "flavors/bitter",
        "flavors/sour",
        "flavors/sweet",
        "publicprompts/plush-toy",
        "referencing-colors",
        "shapes",
        "variant",
        "weighted-animals/heavy",
        "weighted-animals/light",
    }
    assert set(root.collections) == {
        "animal",
        "clothing",  # from pantry YAML
        "colors-cold",  # .txt
        "colors-warm",  # .txt
        "referencing-colors",  # .txt
        "shapes",  # flat list YAML
        "variant",  # .txt
        "dupes",  # .txt
    }
    assert set(root.child_nodes["animals"].collections) == {
        "all-references",
        "mystical",
    }
    assert set(root.child_nodes["animals"].child_nodes["mammals"].collections) == {
        "canine",
        "feline",
    }
    assert set(root.child_nodes["animals"].child_nodes["reptiles"].collections) == {
        "lizards",
        "snakes",
    }, "animals/reptiles does not match"
    assert set(root.child_nodes["animals"].walk_full_names()) == {
        "animals/all-references",
        "animals/mammals/canine",
        "animals/mammals/feline",
        "animals/mystical",
        "animals/reptiles/lizards",
        "animals/reptiles/snakes"
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
    assert set(wildcard_manager.get_values("flavors\\*")) == {
        "chocolate",
        "coffee",
        "dark chocolate",
        "grapefruit",
        "lemon",
        "strawberry",
        "vanilla",
    }


def test_directory_traversal(wildcard_manager: WildcardManager):
    assert not wildcard_manager.get_values("../cant_touch_this")
    assert not wildcard_manager.get_values("..\\cant_touch_this")


@pytest.mark.parametrize("case", ["foo/../bar"])
def test_clean_wildcard_invalid(wildcard_manager: WildcardManager, case: str):
    clean = partial(clean_wildcard, wildcard_wrap=wildcard_manager.wildcard_wrap)
    with pytest.raises(ValueError):
        clean(case)


@pytest.mark.parametrize(
    ("input", "expected"),
    [
        ("foo", "foo"),
        ("foo/bar", "foo/bar"),
        (r"foo\\\\\\\bar//", "foo/bar"),
    ],
)
def test_clean_wildcard(wildcard_manager: WildcardManager, input: str, expected: str):
    ww = wildcard_manager.wildcard_wrap
    assert clean_wildcard(f"{input}", wildcard_wrap=ww) == expected
    assert clean_wildcard(f"{ww}{input}{ww}", wildcard_wrap=ww) == expected


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
        set(wcm.get_values("animals/internet"))
        == set(wcm.get_values("friendos"))
        == internet_animals
    )

    # Wilderness available via symlink?
    assert set(wcm.get_values("wild")) == wild_things
    # ... No directory traversal though!
    assert not wcm.get_values("../outside/wilderness")

    # Now, let's get extra wild and symlink an entire directory...
    wildly_dir = wildcards_dir / "wildly"
    wildly_dir.symlink_to(outside_dir)
    # ... and write some more there!
    wilder_file = wildly_dir / "wilder.txt"
    wilder_file.write_text("whoa!!!")
    wcm.clear_cache()
    assert set(wcm.get_values("wildly/*")) == {
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


def test_wcm_roots():
    """
    Test a WildcardManager that combines multiple trees
    :return:
    """
    wcm = WildcardManager(
        root_map={
            "elaimet": [  # finnish for "animals"
                WILDCARD_DATA_DIR / "animals",
                {
                    "jannat": ListWildcardCollection(["okapi"]),
                },  # exciting animals, incl. an exotic okapi
            ],
            "metasyntactic": [
                {
                    "foo": ListWildcardCollection(["bar", "baz"]),
                    "fnord": ListWildcardCollection(["spam", "eggs"]),
                },
            ],
            "": [
                # The values here will test the convenience list-of-strings syntax
                {
                    # This will appear in the root, as expected
                    "finnish-words": [
                        "kolmivaihevaihtovirtakilowattituntimittari",
                        "törkylempijävongahdus",
                    ],
                    # These cute animals will be merged into the `elaimet/` tree despite the root technically being something else
                    "elaimet/sopot": ["pingviini"],
                },
            ],
        },
    )
    assert wcm.get_collection_names() == {
        "finnish-words",
        "elaimet/jannat",
        "elaimet/all-references",
        "elaimet/mammals/canine",
        "elaimet/mammals/feline",
        "elaimet/mystical",
        "elaimet/reptiles/lizards",
        "elaimet/reptiles/snakes",
        "elaimet/sopot",
        "metasyntactic/fnord",
        "metasyntactic/foo",
    }
    assert {
        v for v in wcm.get_values("elaimet/*").string_values if not v.startswith("_")
    } == {
        "cat",
        "cobra",
        "dog",
        "gecko",
        "iguana",
        "okapi",
        "pingviini",
        "python",
        "tiger",
        "unicorn",
        "wolf",
    }
    assert set(wcm.get_values("metasy*")) == {"eggs", "spam", "baz", "bar"}


def test_weight_parsing(wildcard_manager: WildcardManager):
    """
    Test that parsing the various formats that have weights set do work correctly.
    """
    name_to_entry = {
        str(e): e for e in wildcard_manager.get_values("weighted-animals/*")
    }
    assert name_to_entry["cat"].weight == 3
    assert name_to_entry["elephant"].weight == 50
    assert name_to_entry["rhino"].weight == 20.5
