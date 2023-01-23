import pytest
from dynamicprompts.generators.attentiongenerator import (
    AttentionGenerator,
    DummyGenerator,
)


@pytest.mark.slow
class TestAttentionGenerator:
    def test_default_generator(self):
        pytest.importorskip("spacy")
        generator = AttentionGenerator()
        assert isinstance(generator._prompt_generator, DummyGenerator)
