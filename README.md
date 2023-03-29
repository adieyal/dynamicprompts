# Dynamic Prompts


![MIT](https://img.shields.io/github/license/adieyal/dynamicprompts)
&nbsp;-&nbsp;
![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/adieyal/dynamicprompts/test.yml)
[![Codecov](https://img.shields.io/codecov/c/github/adieyal/dynamicprompts)](https://app.codecov.io/gh/adieyal/dynamicprompts)
&nbsp;-&nbsp;
[![PyPI](https://img.shields.io/pypi/v/dynamicprompts)](https://pypi.org/project/dynamicprompts) ![PyPI - Downloads](https://img.shields.io/pypi/dm/dynamicprompts)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/dynamicprompts)

Dynamicprompts is a Python library that provides developers with a flexible and intuitive templating language for generating prompts for text-to-image generators like Stable Diffusion, MidJourney or Dall-e 2. Dynamicprompts lets you create and manage sophisticated prompt generation workflows that seamlessly integrate with your existing text-to-image generation pipelines.

It includes:
* An easy-to-learn templating language that lets you create a number of unique prompts from a single template.
* Support for wildcard files as placeholders in templates.
* A mechanism for creating a wildcard library. Text, JSON, and YAML files are supported.
* Exhaustive generation of all prompts from a template.
* Variable assignment enabling re-usable prompt snippets. (coming soon)
* Supports Magic Prompt which automatically spices up your prompt with modifiers
* Provides an I'm Feeling Lucky feature which uses the semantic search on Lexica.art to find similar prompts.
* For systems that support attention syntax, Attention Grabber will emphasis random phrases in your prompt.
* Jinja-powered templating for advanced prompt creation.

The dynamicprompts library powers the [Dynamic Prompts](https://github.com/adieyal/sd-dynamic-prompts) extension for Automatic1111.

## Table of contents

* [Dynamic Prompts](#dynamic-prompts)
   * [Quick overview of the templating language:](#quick-overview-of-the-templating-language)
      * [Variants](#variants)
      * [Choosing multiple variants](#choosing-multiple-variants)
      * [Wildcards](#wildcards)
      * [Let's try a real-world prompt](#lets-try-a-real-world-prompt)
      * [Use whitespace for readability](#use-whitespace-for-readability)
   * [Installation](#installation)
   * [Quick Start](#quick-start)
      * [Combinatorial Generation](#combinatorial-generation)
      * [Magic Prompt](#magic-prompt)
       * [I'm feeling lucky](#im-feeling-lucky)
       * [Attention Generator](#attention-generator)
    * [Template syntax](#template-syntax)
      * [Combinations](#combinations)
      * [Wildcard files](#wildcard-files)
      * [Nesting](#nesting)
         * [Combinations](#combinations-1)
         * [Wildcard files](#wildcard-files-1)
      * [Comments](#comments)
      * [Whitespace](#whitespace)
      * [Samplers](#samplers)
         * [Finite Samplers](#finite-samplers)
         * [Non-finite samplers](#non-finite-samplers)
         * [Comparison between samplers](#comparison-between-samplers)
         * [Mixing samplers in the same prompt](#mixing-samplers-in-the-same-prompt)
      * [Syntax customisation](#syntax-customisation)
    * [Wildcard Collections](#wildcard-collections)
    * [Dynamic Prompts in the wild.](#dynamic-prompts-in-the-wild)
    



## Quick overview of the templating language:

### Variants
```
{summer|autumn|winter|spring} is coming
```
Randomly generate one of:
```
summer is coming
autumn is coming
winter is coming
spring is coming
```

### Choosing multiple variants
This syntax `{2$$ and $$A|B|C}` will choose two values from the list:
```
A and B
A and C
B and A
B and C
C and A
C and B
```

### Wildcards
```
__season__ is coming
```
Randomly selects a value from season.txt in your wildcard directory.


### Let's try a real-world prompt
One prompt template can generate a family of prompts:

```
Funky pop {yoda|darth vader|jabba the hutt|princess leia|chewbacca|luke skywalker} figurine, made of {wood|plastic|metal|stone}, product studio shot, on a white background, diffused lighting, centered
```

<img src="images/funkypop.jpg" style="width:50%">

<br/>


Now, how about two characters at the same time:

```
Funky pop {2$$ and $$yoda|darth vader|jabba the hutt|princess leia|chewbacca|luke skywalker} figurine, made of {wood|plastic|metal|stone}, product studio shot, on a white background, diffused lighting, centered
```

<img src="images/funkypop2.jpg" style="width:50%">


<br/>

### Use whitespace for readability
```
# Add comments like this
Funky pop
    {2$$ and $$
  	    yoda
		|darth vader
		|jabba the hutt
		|princess leia
		|chewbacca
		|luke skywalker
	}
	figurine, made of
	{
		wood
		|plastic
		|metal
		|stone
	}, product studio shot, on a white background, diffused lighting, centered
```


Use wildcards for re-usable lists:

```
# starwars.txt
yoda
darth vader
jabba the hutt
princess leia
chewbacca
luke skywalker
```

```
# material.txt
wood
plastic
metal
stone
```

```
# studio-shot.txt
product studio shot, on a white background, diffused lighting, centered
```

Now compose your prompt like this:
```
Funky pop __starwars__ figurine, made of __material__, __studio-shot__
```

and easily change it to:
```
Funky pop __celebrities__ figurine, made of __material__, __studio-shot__
```


Hat tip to [publicprompts](https://publicprompts.art/) for the funky pop prompt.

More complete documentation can be found [below](#syntax).


## Installation

`pip install dynamicprompts`

Additional functionality (see below) can be installed with this command:

`pip install "dynamicprompts[magicprompt, attentiongrabber]"`

## Quick Start

Use the RandomPromptGenerator to create 5 random prompts using a given template:

```python
from dynamicprompts.generators import RandomPromptGenerator

generator = RandomPromptGenerator()
generator.generate("I love {red|green|blue} roses", num_images=5)

>> ['I love blue roses', 'I love red roses', 'I love green roses', 'I love red roses', 'I love red roses']
```

If you want to use wildcards, instantiate a WildcardManager:

```python
from pathlib import Path
from dynamicprompts.generators import RandomPromptGenerator
from dynamicprompts.wildcardmanager import WildcardManager

wm = WildcardManager(Path("/path/to/wildcard/directory"))

generator = RandomPromptGenerator(wildcard_manager=wm)
```

Assuming you have a file called colours.txt in /path/to/wildcards/directory with one colour per line, e.g.

```
red
green
blue
purple
yellow
```

then

```python
generator.generate("I love __colours__ roses", num_prompts)
>> ['I love pink roses', 'I love violet roses', 'I love white roses', 'I love violet roses', 'I love blue roses']
```


### Combinatorial Generation
Instead of generating random prompts from a template, combinatorial generation produces every possible prompt from the given string. For example:

`I {love|hate} {New York|Chicago} in {June|July|August}`

will produce:
> I love New York in June<br>
> I love New York in July<br>
> I love New York in August<br>
> I love Chicago in June<br>
> I love Chicago in July<br>
> I love Chicago in August<br>
> I hate New York in June<br>
> I hate New York in July<br>
> I hate New York in August<br>
> I hate Chicago in June<br>
> I hate Chicago in July<br>
> I hate Chicago in August<br>

If a `__wildcard__` is provided, then a new prompt will be produced for every value in the wildcard file. For example:

`My favourite season is __seasons__`

will produce:
> My favourite season is Summer<br>
> My favourite season is August<br>
> My favourite season is Winter<br>
> My favourite season is Sprint<br>

#### Usage

```python
from dynamicprompts.generators import CombinatorialPromptGenerator

generator = CombinatorialPromptGenerator()
generator.generate("I love {red|green|blue} roses", max_prompts=5)

>> ['I love red roses', 'I love green roses', 'I love blue roses']
```

Notice that only 3 prompts were generated, even though we requested 5. Since there are only three options, i.e. red, green, and blue, only 3 unique prompts can be created. `num_prompts` in this case acts as an upper bound. Combinatorial generation can very quickly produce many more prompts than you intended. `num_prompts` is a safeguard to ensure that you don't accidentally produced thousands or tens of thousands of prompts.

Consider this template:

`My favourite colours are __colours__, __colours__, and __colours__`

If colours.txt contains 10 different colours, a combinatorial enumeration of that template will create `10 * 10 * 10 = 1000` different prompts. e.g.

> My favourite colours are red, green, and blue<br>
> My favourite colours are red, green, and yellow<br>
> My favourite colours are red, green, and purple<br>
> My favourite colours are red, blue, and yellow<br>
> My favourite colours are red, blue, and purple<br>
> ...<br>


### Magic Prompt
Using [Gustavosta](https://huggingface.co/Gustavosta/MagicPrompt-Stable-Diffusion)'s MagicPrompt model, automatically generate new prompts from the input. Trained on 80,000 prompts from [Lexica.art](lexica.art), it can help give you interesting new prompts on a given subject. Here are some automatically generated variations for "dogs playing football":

> dogs playing football, in the streets of a japanese town at night, with people watching in wonder, in the style of studio ghibli and makoto shinkai, highly detailed digital art, trending on artstation<br>
> dogs playing football, in the background is a nuclear explosion. photorealism. hq. hyper. realistic. 4 k. award winning.<br>
> dogs playing football, in the background is a nuclear explosion. photorealistic. realism. 4 k wideshot. cinematic. unreal engine. artgerm. marc simonetti. jc leyendecker<br>

This is compatible with the wildcard syntax described above.

#### Usage

```python
from dynamicprompts.generators import RandomPromptGenerator
from dynamicprompts.generators.magicprompt import MagicPromptGenerator

generator = RandomPromptGenerator()
magic_generator = MagicPromptGenerator(generator, device=0) # device = 0 for CUDA or -1 for CPU

num_prompts = 5
generator.generate("I love {red|green|blue} roses", num_prompts)

>> ['I love red roses trending on artstation #vividart #pixiv', 'I love red roses trending on artstation artwork', 'I love blue roses breakfast club, cute, intricate, highly detailed, digital painting, artstation, concept art, smooth, sharp focus, illustration, unreal engine 5, 8 k, art by artgerm and greg rutkowski and alphonse mucha', 'I love green roses I love green flowers, smile, Tristan Eaton, victo ngai, artgerm, RHADS, ross draws', 'I love red roses smile, Tristan Eaton, victo ngai, artgerm, RHADS, ross draws']

```

The first time you use it, the model is downloaded. It is approximately 500mb and so will take some time depending on how fast your connection is. It will also take a few seconds on first activation as the model is loaded into memory. Note, if you're low in VRAM, you might get a Cuda error. My GPU uses less than 8GB by YMMV.

Magic Prompt is not available by default, you need to install it as follows:

`pip install "dynamicprompts[magicprompt]"`

#### Other models
There a few alternatives to Gustavosta's model available. You can try:

```
magic_generator = MagicPromptGenerator(generator, "AUTOMATIC/promptgen-lexart")
magic_generator = MagicPromptGenerator(generator, "AUTOMATIC/promptgen-majinai-safe")
magic_generator = MagicPromptGenerator(generator, "AUTOMATIC/promptgen-majinai-unsafe")
```

You can find a longer list [here](https://github.com/adieyal/sd-dynamic-prompts/blob/main/config/magicprompt_models.txt)
Note that each model requires a download of large model files.

### I'm feeling lucky
Use the [lexica.art](https://lexica.art) API to create random prompts. Useful if you're looking for inspiration, or are simply too lazy to think of your own prompts. When this option is selected, the template is used as a search string. For example, prompt "Mech warrior" might return:

> A large robot stone statue in the middle of a forest by Greg Rutkowski, Sung Choi, Mitchell Mohrhauser, Maciej Kuciara, Johnson Ting, Maxim Verehin, Peter Konig, final fantasy , 8k photorealistic, cinematic lighting, HD, high details, atmospheric,

> a beautiful portrait painting of a ( ( ( cyberpunk ) ) ) armor by simon stalenhag and pascal blanche and alphonse mucha and nekro. in style of digital art. colorful comic, film noirs, symmetry, brush stroke, vibrating colors, hyper detailed. octane render. trending on artstation

> symmetry!! portrait of a robot astronaut, floral! horizon zero dawn machine, intricate, elegant, highly detailed, digital painting, artstation, concept art, smooth, sharp focus, illustration, art by artgerm and greg rutkowski and alphonse mucha, 8 k

<img src="images/feeling-lucky.png">

#### Usage

```python
from dynamicprompts.generators import RandomPromptGenerator
from dynamicprompts.generators.feelinglucky import FeelingLuckyGenerator

generator = RandomPromptGenerator()
lucky_generator = FeelingLuckyGenerator(generator)

num_prompts = 5
lucky_generator.generate("I love {red|green|blue} roses", num_prompts)

>> ['“ guns and roses ” ', '🌹🥀🏜. 🌌🌠⭐. 💯. ', 'tattoo design, stencil, beautiful japanese girls face, roses and ivy surrounding by artgerm, artgerm, cat girl, anime ', 'rose made of glass dramatic lighting', 'a wireframe render of a red rose']

```

### Attention Generator
If you are using [Automatic1111](https://github.com/AUTOMATIC1111/stable-diffusion-webui/) or a similar frontend to Stable Diffusion that uses attention syntax, e.g. `(some text:1.4)`, AttentionGenerator will randomly add attention to various phrases in your prompt. This injects a small amount of randomness into your prompt.

#### Usage

```python
from dynamicprompts.generators import RandomPromptGenerator
from dynamicprompts.generators.attentiongenerator import AttentionGenerator

generator = RandomPromptGenerator()
attention_generator = AttentionGenerator(generator)

prompt = "a portrait an anthropomorphic panda mage casting a spell, wearing mage robes, landscape in background, cute, dnd character art portrait, by jason felix and peter mohrbacher, cinematic lighting"
attention_generator.generate(prompt, num_prompts=1)

>> ['a portrait an anthropomorphic panda mage casting a spell, wearing (mage robes:0.77), landscape in background, cute, dnd character art portrait, by jason felix and peter mohrbacher, cinematic lighting']

```

<img src="images/emphasis.png">

Note, AttentionGenerator is not installed by default as it needs additional libraries to run. Use this command to install it:

`pip install "dynamicprompts[attentiongrabber]"`

One your first use it, a model will automatically be downloaded.

## Template syntax

The templating language understands 3 different core constructs:
* Literals - this is plain text, e.g. `A red rose`
* [wildcards](https://github.com/adieyal/sd-dynamic-prompts/blob/main/docs/SYNTAX.md#wildcard-files) - a wildcard represent a variable that is populated from a file, e.g. `A __colours__ rose` - a prompt will be generated by randomly choosing a value from a file called colours.txt in the [wildcards directory](https://github.com/adieyal/sd-dynamic-prompts#wildcard_dir)
* [variants or combinations](https://github.com/adieyal/sd-dynamic-prompts/blob/main/docs/SYNTAX.md#combinations) - `A {red|pink|white} rose` - Dynamic Prompts will chose one of the colours at random when generating the prompt. They are called combinations because syntax is available to choose more than one value at once, `A {2$$red|pink|white} rose` will generate one of: A red,pink rose, A red,white rose, A pink,red rose, .... etc.

### Combinations
	{2$$opt1|opt2|opt3}

This will randomly combine two of the options for every batch, separated with a comma.  In this case, "opt1, opt2" or "opt2, opt3", or "opt1, opt3" or the same pairs in the reverse order.

	{1-3$$opt1|opt2|opt3}

This will use a random number of options between 1 and 3 for each batch.

If the number of combinations chosen is greater than the number of options listed then options may be repeated in the output.
If the number of combinations chosen is less than or equal to the number of options listed then the same options will not be chosen more than once.

	{4$$and$$opt1|opt2|opt3|opt4|opt5}

This will choose 4 options and join them together with 'and' instead of the default comma. When there are multiple $$ tokens then the first item is the number of options to choose and the second option is the joiner to use.

	{-$$opt1|opt2|opt3}

An omitted minimum is assumed to be 0 and an omitted maximum is assumed to be the number of options.

	{opt1|opt2|opt3}

If you omit the `$$` prefix, one item will be selected. (Equivalent to `1$$`)

Options are chosen randomly with replacement. This means that `{2$$opt1|opt2}` can return any of the following:

> opt1, opt1<br>
> opt1, opt2<br>
> opt2, opt1<br>
> opt2, opt2<br>

This is useful in conjunction with wildcards (see below).


Options can be assigned relative weights using a `::` prefix operator.

	photo of a {3::blue|red} ball

This will generate 3 photos of a blue ball per every 1 photo of a red ball.

<img src="images/weighting-colours.png">

	photo of a {blue|0.25::red} ball

Decimals also work as expected: this will generate 4 photos of a blue ball per every 1 photo of a red ball.

	photo portrait of a {59::white|21::latino|14::black|8::asian} {man|woman}

This would generate photo portraits of men and women of different races, proportional to the 2020 U.S. census.
<img src="images/weighting-us-population.png">

If you omit the `::` prefix, it will have a default weight of 1.0. (Equivalent to `1::prompt`)

### Wildcard files
Wildcards are text files (ending in .txt). Each line contains a term, artist name, or modifier. The wildcard file can then be embedded in your prompt by removing the .txt extension and surrounding it with double underscores. e.g:

	My favourite colour is __colours__

Empty lines and lines starting with `#` are ignored. This can be used to add comments or disable sections of the file.

Mixing Combinations and Wildcards can be useful. For example,

	a photo of a {2-4$$and$$__adjective__} house

will choose between 2 and 4 options from adjective.txt, join them together with "and", for results such as "a photo of a cozy and ancient and delicate house"


### Nesting

Many constructed can nest sub-prompts. This means that you can create more advanced templates. Here are some examples:

#### Combinations
You can nest inside combinations.

    {__seasons__|__timeofday__}


This will then either choose a season from seasons.txt or a time of day from timeofday.txt.

Combinations can also be nested inside other combinations, e.g.

    {{a|b|c}|d}

You can even nest complete prompts in combinations:

	{A {small|large} __monster__|A {scary|friendly} ghost}

This produce one of:

> A small dragon (assuming dragon is contained in the monster.txt file)<br>
> A large dragon<br>
> A scary ghost<br>
> A friendly ghost<br>

If you find that your prompts are becoming too complicated to read, consider using [whitespace](#whitespace)

#### Wildcard files
Wildcard files are processed recursively. If a wildcard file contains a row with dynamic syntax, then that will be resolved as well. For example if seasons.txt contains the following rows:

	Summer
	Winter
	{Autumn|Fall}
	Spring

if the 3rd row is chosen, then either Autumn or Fall will be selected. You could go pretty wild e.g.

	Summer
	__winter_in_different_languages__
	{Autumn|Fall}
	Spring

### Comments
Python-style comments are supported:

    Test string
    # This  a comment until the end of the line

### Whitespace
In most cases, whitespace is ignored which allows you to create more expressive and readable prompts, e.g.

	wisdom {
    	woman, __colours__ eyes, braided hair
    	|man using a __war/weapons/swords/european__, red turban
    	|dwarf wielding a warhammer, __colours__ beard
	},
	knows the meaning of life, warrior, hyper-realistic, peaceful, dark fantasy, unreal engine, 8k

### Samplers
[Note, this is an advanced feature and you probably don't need to worry about it.]

Behind the scenes, Dynamic Prompts uses samplers to select an option from a wildcard or variant. Samplers can be classed as either finite or non-finite.

#### Finite Samplers
When sampling using a finite sampler, once the options are exhausted, the sampler no-longer returns any values.

The only finite sampler currently available is the  **Combinatorial Sampler**.  It will exhaustively generate all possible combinations and then stop, e.g. `{A|B|C}` will produce:

```
A
B
C
```

CombinatorialPromptGenerators uses a combinatorial sampler by default.

#### Non-finite samplers
Non-finite samplers can be used to generate an infinite number of prompts. They are useful for generating prompts that are not limited by the number of options available in a wildcard file or combination.

**Random Sampler** - this sampler randomly picks an option. In this case `A`, `B`, and `C` are all equally likely to be chosen, e.g.
```
A
C
B
B
A
C
...
```

Unsurprisingly, RandomPromptGenerators uses a random sampler by default.

**Cyclical Sampler** - a cyclical sampler will choose an item in a round-robin fashion. Every time you sample using this sampler, it will return the next option in the list. Once you have exhausted the list it starts again. e.g.:
```
A
B
C
A
B
...
```

Both Random and Cyclical samplers treat a wildcard or variant in isolation, whereas the Combinatorial sampler combines all the wildcards and variants in the prompt and treats them as a single unit.  The examples below should make this clearer.

#### Comparison between samplers
Consider the prompt `{A|B|C} {X|Y}`. If we use a random sampler, we might get the following prompts:

```
A X
C Y
B X
A Y
C X
C X
```

If we use a cyclical sampler, we will generate the following prompts:
```
A X
B Y
C X
A Y
B X
C Y
A X
...

```

Finally, if we use a combinatorial sampler, we will generate exactly 6 prompts:
```
A X
A Y
B X
B Y
C X
C Y
```

#### Mixing samplers in the same prompt
When parsing a prompt template, every variant and wildcard is assigned a sampler. If a sampler is not explicitly set, then the default sampler is used. You can explictly set the sampler, using the syntax `{!A|B|C}` or `__!wildcard__` for combinatorial, `{~A|B|C}` or `__~wildcard__` for random and `{@A|B|C}` or `__@wildcard__` for cyclical.

Examples:
In combinatorial mode, the template `{A|B|C} {@X|Y}` will automatically be converted to `{!A|B|C} {@X|Y}`. This will generate the following prompts:
```
A X
B Y
C X
```

This template only produces 3 prompts because the combinatorial sampler is exhausted  after producing `A`, `B`, and `C`.

Similarly, `{!A|B|C} {~X|Y}` might generate the following prompts:
```
A Y
B X
C X
```

Compare this with `{!A|B|C} {!X|Y}` which will generate the following prompts:
```
A X
A Y
B X
B Y
C X
C Y
```

The default mode is propagated to all nested variants and wildcards, e.g. In random mode, this prompt:
```
{A|B|C}
{@X|Y|
    {1|2|3}
}
```

will be converted to:
```
{~A|B|C}
{@X|Y|
	{@1|2|3}
}
```

One final note, finite variants and wildcards cannot be sampled inside non-finite variants and wildcards. For example, in this prompt:
```
{~A|B|{!X|Y}}
```

the combinatorial syntax is ignored and the template will be converted to:
```
{~A|B|{~X|Y}}
```


### Syntax customisation
To address potential syntax clashes with other tools it is possible to change various tokens. Instead of `{red|green|blue}` you can configure the library to use the `<` `>` pair instead, e.g. `<red|green|blue>`. You can also change the `__` used in wildcards. So instead of `__colours__`, you can configure wildcards to use `**`, e.g. `**colours**`
```python

from pathlib import Path
from dynamicprompts.wildcards import WildcardManager
from dynamicprompts.generators import RandomPromptGenerator
from dynamicprompts.parser.config import ParserConfig

WILDCARD_DIR = Path("/path/to/wildcards/directory")
wm = WildcardManager(WILDCARD_DIR)
parser_config = ParserConfig(variant_start="<", variant_end=">", wildcard_wrap="**")

generator = RandomPromptGenerator(wm, parser_config=parser_config)

```
## Wildcard Collections
You can bootstrap your wildcard library by using our [pre-existing collections](https://github.com/adieyal/sd-dynamic-prompts/tree/main/collections). You'll find just under 80,000 wildcards divided into 1900 files. Feel free to pick and choose or take them in their entirety.

## Dynamic Prompts in the wild.
Dynamic Prompts has been used in:
1. [SD Dynamic Prompts](https://github.com/adieyal/sd-dynamic-prompts/edit/main/README.md) Auto1111 extension
2. Deforum 0.7 [colab](https://colab.research.google.com/drive/1qtYHUwFl9ocLyzDRL1_MlpQluV32ndoT?usp=sharing)
