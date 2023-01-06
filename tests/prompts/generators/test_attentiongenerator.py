import pytest

try:
    from dynamicprompts.generators import AttentionGenerator, DummyGenerator
except ImportError:
    pass

@pytest.mark.attentiongenerator
class TestAttentionGenerator:
    def test_default_generator(self):
        generator = AttentionGenerator()
        assert isinstance(generator._prompt_generator, DummyGenerator)