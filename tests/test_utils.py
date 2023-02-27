from dynamicprompts.utils import dedupe, removeprefix, removesuffix


def test_dedupe():
    arr = ["a", "b", "a", "c", "b", "d"]
    assert dedupe(arr) == ("a", "b", "c", "d")


def test_remove_prefix():
    assert removeprefix("foobar", "foo") == "bar"
    assert removeprefix("foobar", "bar") == "foobar"


def test_remove_suffix():
    assert removesuffix("foobar", "bar") == "foo"
    assert removesuffix("foobar", "foo") == "foobar"
