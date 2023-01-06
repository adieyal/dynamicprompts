0.1.19 - Added the Jinja2 generator from the SD Dynamic Prompts extension. Also fixed the Jinja2 interface to match the other generators
0.1.18 - Removed explicit dependency on pytorch, added default arguments for number of prompts produced by DummyGenerator and RandomPromptGenerator
0.1.17 - Fixed alternating words syntax [cat|dog] - pipes are only reserved inside variants. Also standardised MagicPrompt, AttentionGenerator, and FeelinLucky to use a DummyGenerator by default so that users are not forced to provide an alternative generator if one isn't needed.
0.1.16 - Changed type annotations to use classes from the typing package instead of native type in order to support python 3.7
0.1.15 - First public release
