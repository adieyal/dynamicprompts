from dynamicprompts.utils import dedupe


def test_dedupe():
    arr = ["a", "b", "a", "c", "b", "d"]
    assert dedupe(arr) == ("a", "b", "c", "d")
