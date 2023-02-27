from unittest.mock import Mock, patch

from dynamicprompts.generators import DummyGenerator, FeelingLuckyGenerator


class TestFeelingLucky:
    def test_default_generator(self):
        generator = FeelingLuckyGenerator()
        assert isinstance(generator._generator, DummyGenerator)

    def test_generate(self):
        results = [{"prompt": "ABC"}, {"prompt": "XYZ"}]
        with patch("dynamicprompts.generators.feelinglucky.requests") as mock_response:
            with patch("dynamicprompts.generators.feelinglucky.random") as mock_random:
                mock_generator = Mock()
                mock_generator.generate.return_value = ["Prompt"]

                m = Mock()
                m.json.return_value = {"images": results}
                mock_response.get.return_value = m
                mock_random.choices.return_value = [results[0]]

                generator = FeelingLuckyGenerator(mock_generator)
                prompts = generator.generate("This is a test", 1)
                assert len(prompts) == 1
                assert prompts[0] == results[0]["prompt"]

                mock_generator.generate.assert_called_with("This is a test", 1)

                mock_random.choices.assert_called_with(results, k=1)
