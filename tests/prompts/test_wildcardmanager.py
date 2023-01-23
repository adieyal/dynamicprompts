from dynamicprompts.wildcardmanager import WildcardManager


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
        ['__colors-cold__', '__colors-warm__'],  # Top level
        {  # child folders
            'animals': (
                ['__animals/mystical__'],
                {'mammals': (
                    ['__animals/mammals/canine__', '__animals/mammals/feline__'],
                    {},
                )},
            ),
            'flavors': (
                ['__flavors/sour__', '__flavors/sweet__'],
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
