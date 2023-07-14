from pathlib import Path

import pytest
from dynamicprompts.wildcards.collection.text_file import WildcardTextFile


@pytest.fixture
def wildcard_text_file():
    path = Path(__file__).parent.parent.parent / "test_data" / "wildcards" / "dupes.txt"

    return WildcardTextFile(path)


def test_get_values(wildcard_text_file):
    expected = ["red", "blue", "blue", "green", "red"]
    assert wildcard_text_file.get_values() == expected
