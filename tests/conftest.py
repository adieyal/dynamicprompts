from pathlib import Path

import pytest
from dynamicprompts.wildcardmanager import WildcardManager

WILDCARD_DATA_DIR = Path(__file__).parent / "test_data" / "wildcards"
assert WILDCARD_DATA_DIR.is_dir()


@pytest.fixture
def wildcard_manager() -> WildcardManager:
    return WildcardManager(WILDCARD_DATA_DIR)
