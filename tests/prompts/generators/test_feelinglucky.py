import pytest
from unittest import mock

from dynamicprompts.generators import FeelingLuckyGenerator
class TestFeelingLucky:
    def test_generate(self):
        results = [{"prompt": "ABC"}, {"prompt": "XYZ"}]
        with mock.patch("dynamicprompts.generators.feelinglucky.requests") as mock_response:
            with mock.patch("dynamicprompts.generators.feelinglucky.random") as mock_random:
                m = mock.Mock()
                m.json.return_value = {"images": results}
                mock_response.get.return_value = m
                mock_random.choices.return_value = [results[0]]

                generator = FeelingLuckyGenerator()
                prompts = generator.generate("This is a test", 1)
                assert len(prompts) == 1
                assert prompts[0] == results[0]["prompt"]

                mock_random.choices.assert_called_with(results, k=1)