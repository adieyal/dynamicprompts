from dynamicprompts.generators.attentiongenerator import AttentionGenerator, DummyGenerator

class TestAttentionGenerator:
    def test_default_generator(self):
        generator = AttentionGenerator()
        assert isinstance(generator._prompt_generator, DummyGenerator)