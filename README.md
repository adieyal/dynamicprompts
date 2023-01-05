# Dynamic Prompts
A library that provides tools and a templating language for designing prompts for text-to-image generators such as Stable Diffusion. This is useful if you would like to generate a number of new prompts using a template. 

The following template

	A {house|apartment|lodge|cottage} in {summer|winter|autumn|spring} by {2$$artist1|artist2|artist3}

will produce any of the following prompts:

> A **house** in **summer** by **artist1**, **artist2**<br>
> A **lodge** in **autumn** by **artist3**, **artist1**<br>
> A **cottage** in **winter** by **artist2**, **artist3**<br>
> ...<br>

You can use these templates like these to search for interesting combinations of artists and styles.

You can also pick a random string from a file. Assuming you have the file seasons.txt in WILDCARD_DIR (see below), then:

    __seasons__ is coming

Might generate the following:

> Winter is coming<br>
> Spring is coming<br>
> ...<br>

You can also use the same wildcard twice

    I love __seasons__ better than __seasons__

> I love Winter better than Summer<br>
> I love Spring better than Spring<br>

More complete documentation can be found [below](#syntax).

## Installation

`pip install dynamicprompts`

Additional functionality (see below) can be installed with this command:

`pip install "dynamicprompts[magicprompt, attentiongrabber]"`

## Quick Start

Use the RandomPromptGenerator to create 5 random prompts using a given template:

```
from pathlib import Path
from dynamicprompts.wildcardmanager import WildcardManager
from dynamicprompts.generators import RandomPromptGenerator

WILDCARD_DIR = Path("/path/to/wildcards/directory")
wm = WildcardManager(WILDCARD_DIR)

generator = RandomPromptGenerator(wm)
num_prompts = 5
generator.generate("I love {red|green|blue} roses", num_prompts)

>> ['I love blue roses', 'I love red roses', 'I love green roses', 'I love red roses', 'I love red roses']
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

```
generator.generate("I love __colours__ roses", num_prompts)
>> ['I love pink roses', 'I love violet roses', 'I love white roses', 'I love violet roses', 'I love blue roses']
```

See more examples below.

## Combinatorial Generation
Instead of generating random prompts from a template, combinatorial generation produced every possible prompt from the given string. For example:

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

### Usage
```
from pathlib import Path
from dynamicprompts.wildcardmanager import WildcardManager
from dynamicprompts.generators import CombinatorialPromptGenerator

WILDCARD_DIR = Path("/path/to/wildcards/directory")
wm = WildcardManager(WILDCARD_DIR)

generator = CombinatorialPromptGenerator(wm)

num_prompts = 5
generator.generate("I love {red|green|blue} roses", num_prompts)

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


## Magic Prompt
Using [Gustavosta](https://huggingface.co/Gustavosta/MagicPrompt-Stable-Diffusion)'s MagicPrompt model, automatically generate new prompts from the input. Trained on 80,000 prompts from [Lexica.art](lexica.art), it can help give you interesting new prompts on a given subject. Here are some automatically generated variations for "dogs playing football":

> dogs playing football, in the streets of a japanese town at night, with people watching in wonder, in the style of studio ghibli and makoto shinkai, highly detailed digital art, trending on artstation<br>
> dogs playing football, in the background is a nuclear explosion. photorealism. hq. hyper. realistic. 4 k. award winning.<br>
> dogs playing football, in the background is a nuclear explosion. photorealistic. realism. 4 k wideshot. cinematic. unreal engine. artgerm. marc simonetti. jc leyendecker<br>

This is compatible with the wildcard syntax described above.

The first time you use it, the model is downloaded. It is approximately 500mb and so will take some time depending on how fast your connection is. It will also take a few seconds on first activation as the model is loaded into memory. Note, if you're low in VRAM, you might get a Cuda error. My GPU uses less than 8GB by YMMV.

Magic Prompt is not available by default, you need to install it as follows:

`pip install "dynamicprompts[magicprompt]"`

### Usage
```
from pathlib import Path
from dynamicprompts.wildcardmanager import WildcardManager
from dynamicprompts.generators import RandomPromptGenerator
from dynamicprompts.generators.magicprompt import MagicPromptGenerator

WILDCARD_DIR = Path("/path/to/wildcards/directory")
wm = WildcardManager(WILDCARD_DIR)

generator = RandomPromptGenerator(wm)
magic_generator = MagicPromptGenerator(generator, device=0) # device = 0 for CUDA or -1 for CPU

num_prompts = 5
generator.generate("I love {red|green|blue} roses", num_prompts)

>> ['I love red roses trending on artstation #vividart #pixiv', 'I love red roses trending on artstation artwork', 'I love blue roses breakfast club, cute, intricate, highly detailed, digital painting, artstation, concept art, smooth, sharp focus, illustration, unreal engine 5, 8 k, art by artgerm and greg rutkowski and alphonse mucha', 'I love green roses I love green flowers, smile, Tristan Eaton, victo ngai, artgerm, RHADS, ross draws', 'I love red roses smile, Tristan Eaton, victo ngai, artgerm, RHADS, ross draws']

```

## I'm feeling lucky
Use the [lexica.art](https://lexica.art) API to create random prompts. Useful if you're looking for inspiration, or are simply too lazy to think of your own prompts. When this option is selected, the template is used as a search string. For example, prompt "Mech warrior" might return:

> A large robot stone statue in the middle of a forest by Greg Rutkowski, Sung Choi, Mitchell Mohrhauser, Maciej Kuciara, Johnson Ting, Maxim Verehin, Peter Konig, final fantasy , 8k photorealistic, cinematic lighting, HD, high details, atmospheric,

> a beautiful portrait painting of a ( ( ( cyberpunk ) ) ) armor by simon stalenhag and pascal blanche and alphonse mucha and nekro. in style of digital art. colorful comic, film noirs, symmetry, brush stroke, vibrating colors, hyper detailed. octane render. trending on artstation

> symmetry!! portrait of a robot astronaut, floral! horizon zero dawn machine, intricate, elegant, highly detailed, digital painting, artstation, concept art, smooth, sharp focus, illustration, art by artgerm and greg rutkowski and alphonse mucha, 8 k

<img src="images/feeling-lucky.png">

### Usage

```
from pathlib import Path
from dynamicprompts.wildcardmanager import WildcardManager
from dynamicprompts.generators import RandomPromptGenerator
from dynamicprompts.generators.feelinglucky import FeelingLuckyGenerator

generator = RandomPromptGenerator(wm)
lucky_generator = FeelingLuckyGenerator(generator)

num_prompts = 5
lucky_generator.generate("I love {red|green|blue} roses", num_prompts)

>> ['“ guns and roses ” ', '🌹🥀🏜. 🌌🌠⭐. 💯. ', 'tattoo design, stencil, beautiful japanese girls face, roses and ivy surrounding by artgerm, artgerm, cat girl, anime ', 'rose made of glass dramatic lighting', 'a wireframe render of a red rose']

```

## Attention Generator
If you are using [Automatic1111](https://github.com/AUTOMATIC1111/stable-diffusion-webui/) or a similar frontend to Stable Diffusion that uses attention syntax, e.g. `(some text:1.4)`, AttentionGenerator will randomly add attention to various phrases in your prompt. This injects a small amount of randomness into your prompt.

### Usage

```
from pathlib import Path
from dynamicprompts.wildcardmanager import WildcardManager
from dynamicprompts.generators import RandomPromptGenerator
from dynamicprompts.generators.attentiongenerator import AttentionGenerator

WILDCARD_DIR = Path("/path/to/wildcards/directory")
wm = WildcardManager(WILDCARD_DIR)

generator = RandomPromptGenerator(wm)
attention_generator = AttentionGenerator(generator)

num_prompts = 1
prompt = "a portrait an anthropomorphic panda mage casting a spell, wearing mage robes, landscape in background, cute, dnd character art portrait, by jason felix and peter mohrbacher, cinematic lighting"
attention_generator.generate(prompt, num_prompts)

>> ['a portrait an anthropomorphic panda mage casting a spell, wearing (mage robes:0.77), landscape in background, cute, dnd character art portrait, by jason felix and peter mohrbacher, cinematic lighting']

```

<img src="images/emphasis.png">

Note, AttentionGenerator is not installed by default as it needs additional libraries to run. Use this command to install it:

`pip install "dynamicprompts[attentiongrabber]"`

One your first use it, a model will automatically be downloaded.

# Template syntax

The templating language understands 3 different core constructs:
* Literals - this is plain text, e.g. `A red rose`
* [wildcards](https://github.com/adieyal/sd-dynamic-prompts/blob/main/docs/SYNTAX.md#wildcard-files) - a wildcard represent a variable that is populated from a file, e.g. `A __colours__ rose` - a prompt will be generated by randomly choosing a value from a file called colours.txt in the [wildcards directory](https://github.com/adieyal/sd-dynamic-prompts#wildcard_dir)
* [variants or combinations](https://github.com/adieyal/sd-dynamic-prompts/blob/main/docs/SYNTAX.md#combinations) - `A {red|pink|white} rose` - Dynamic Prompts will chose one of the colours at random when generating the prompt. They are called combinations because syntax is available to choose more than one value at once, `A {2$$red|pink|white} rose` will generate one of: A red,pink rose, A red,white rose, A pink,red rose, .... etc.

## Combinations
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

## Wildcard files
Wildcards are text files (ending in .txt). Each line contains a term, artist name, or modifier. The wildcard file can then be embedded in your prompt by removing the .txt extension and surrounding it with double underscores. e.g:

	My favourite colour is __colours__

Empty lines and lines starting with `#` are ignored. This can be used to add comments or disable sections of the file.

Mixing Combinations and Wildcards can be useful. For example,

	a photo of a {2-4$$and$$__adjective__} house

will choose between 2 and 4 options from adjective.txt, join them together with "and", for results such as "a photo of a cozy and ancient and delicate house"


## Nesting

Many constructed can nest sub-prompts. This means that you can create more advanced templates. Here are some examples:

### Combinations
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
> A fiendly ghost<br>

If you find that your prompts are becoming too complicated to read, consider using [whitespace](#whitespace)

### Wildcard files
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

## Comments
Python and c-style comments are supported:

    Test string
    # This  a comment until the end of the line
    // this is also a comment until the end of the line
    {A|/* this is an inline comment */B}

## Whitespace
In most cases, whitespace is ignored which allows you to create more expressive and readable prompts, e.g.

	wisdom {
    	woman, __colours__ eyes, braided hair
    	|man using a __war/weapons/swords/european__, red turban
    	|dwarf weilding a warhammer, __colours__ beard
	}, 
	knows the meaning of life, warrior, hyper-realistic, peaceful, dark fantasy, unreal engine, 8k

## Prompt development
The flexibility provided in the templating language makes it easy to start developing more sophisticated prompts, e.g,here is a prompt for an engagement ring. 

    Elegant solitaire engagement ring. 
    {classic|petite|thin|cigar|tapered|twisted}     # Band design
    {silver|{white|rose|yellow}gold|platinum}       # Band metal
    {round|faceted|honeycomb}                       # Band texture
    band with a
    {round|brilliant|oval|heart-shaped}             # Stone cut
    __items/materials/gems__                        # Gem type. 

Below are some example prompts generated from this pattern:
> Elegant solitaire engagement ring. tapered rose gold round band with a brilliant anthophyllite<br>
> Elegant solitaire engagement ring. thin yellow gold faceted band with a brilliant grandidierite<br>
> Elegant solitaire engagement ring. cigar platinum faceted band with a brilliant tusionite<br>
> Elegant solitaire engagement ring. thin yellow gold honeycomb band with a oval bowenite<br>
> Elegant solitaire engagement ring. classic silver round band with a heart-shaped musgravite<br>
