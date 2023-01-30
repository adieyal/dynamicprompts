import pytest
from dynamicprompts.generators.attentiongenerator import AttentionGenerator


@pytest.mark.slow
def test_default_generator():
    pytest.importorskip("spacy")
    generator = AttentionGenerator()
    for prompt in generator.generate("purple cat singing opera, artistic, painting", 5):
        assert "(purple" in prompt or "(artistic" in prompt or "(painting" in prompt
        assert ")" in prompt
