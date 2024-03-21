# Introduction

Constructing good prompts for Stable Diffusion can be difficult, especially if you're trying to learn through trial and error.

Let's see how this works.

## Getting Started

Suppose you want to create images of a diamond ring; you might start with something like:

    A diamond ring on a gold band.

## Variants

What if we wanted an image of a platinum ring as well? We can use the Dynamic Prompts variant syntax, e.g.

    A diamond ring set on a {gold|platinum} band.

Dynamic Prompts would then generate one of:

    A diamond ring set on a gold band

and

    A diamond ring set on a platinum band

## Nested variant

Gold comes in various varieties, let's add those as well:

    A diamond ring set on a {{rose|yellow|white} gold|platinum} band.

Notice how we nested a variant for the type of gold, i.e. `{rose|yellow|white}` inside the main variant.
So now, when generating an image, one of the following prompts is created:

    A diamond ring set on a rose gold band
    A diamond ring set on a yellow gold band
    A diamond ring set on a white gold band
    A diamond ring set on a platinum band

Nesting variants can quickly make your prompt template hard to read. Luckily, Dynamic Prompts ignores whitespace so that we can change the prompt to:

    A diamond ring set on a {
        {rose|yellow|white} gold   # you can also add comments
        | platinum                 # which will be ignored by the DP parser
    } band

Of course, we're not limited to only one variant; we can add a little more variation like this:

    A {diamond|ruby|emerald} ring set on a {classic|thin|thick}
    {
        {rose|yellow|white} gold
        | platinum
    }
    band

This template could produce any of these prompts:

    A ruby ring set on a classic rose gold band
    A emerald ring set on a thin platinum band
    etc.

That second prompt isn't grammatically correct, it doesn't matter to Stable Diffusion, but if you prefer correct grammar, you can write something like:

    {A diamond|A ruby|An emerald} ring set on a {classic|thin|thick}
    {
        {rose|yellow|white} gold
        | platinum
    }
    band

## Wildcards

What if we had many gems that we would like to use in our rings? You can certainly add them as variants along with rubies and emeralds, but this may become cumbersome with many variants. In this case, we can use a wildcard.

First, we create a file called `gems.txt` inside the wildcards folder. The location depends on the frontend you're using for Dynamic Prompts.
In it, we add one variant per line, e.g.

```
diamond
ruby
emerald
```

Now our prompt changes to:

    A __gems__ ring set on a {classic|thin|thick}
    {
        {rose|yellow|white} gold
        | platinum
    }
    band

`__gems__` is a wildcard and will act as a variant that uses every gem in gems.txt. Note the name of the wildcard is the same as the name of the file, i.e., gems.txt without the .txt at the end. We then add a double underscore `__` to the beginning and end of the wildcard.

Neat!

Wildcard files can use all the same syntax that we can use in our prompts. To demonstrate this, let's create a new file called `precious_metals.txt`. Inside we add:

```
{rose|yellow|white} gold
platinum
silver
```

Move the file into the wildcards folder. Now our prompt looks like this:

    A __gems__ ring set on a {classic|thin|thick} __precious_metals__ band

## Combinatorial Generation

By default, Dynamic Prompts generates random prompts from our template. Each prompt will choose a random gem, random band type, and random precious metal. Let's count the total number of possible rings our template can generate:

    Assume we have ten different types of gems in our gems.txt file
    Three band thicknesses
    Three metals, although gold has three variants, so we actually have five metals.

    The total number of potential prompts is  10 * 3 * 5 = 150 different prompts.

What if we wanted to generate all of them? In that case, we change to combinatorial mode.

## Wildcard Collection

A well-designed wildcard collection can be used as building blocks for creating great prompts without having to reinvent the wheel every time.

The most interesting wildcards are those related to art and artists. It's a great way to explore different styles.

If you like to experiment with styles from multiple artists at the same time, try something like:

    surfer in space, intricate detail, airbrush painting, illustration, by __artists/European Art/modern/pointilism__ and __artists/European Art/modern/american_impressionism__

Here are some prompts that I get using the default collections available in the `sd-dynamic-prompts` extension:

    surfer in space, intricate detail, airbrush painting, illustration, by Vincent van Gogh and Daniel Garber

    surfer in space, intricate detail, airbrush painting, illustration, by Maximilien Luce and Wilson Irvine

    surfer in space, intricate detail, airbrush painting, illustration, by Jean Metzinger and John Elwood Bundy

Dynamic Prompts has syntax to allow you to choose two artists together:

    surfer in space, intricate detail, airbrush painting, illustration, by {2$$__artists/illustrations/childrens_books__}

Some examples of prompts that are generated:

    surfer in space, intricate detail, airbrush painting, illustration, by Todor Dinov,Ray Goossens

    surfer in space, intricate detail, airbrush painting, illustration, by Emily Winfield Martin,Kitty Crowther

    surfer in space, intricate detail, airbrush painting, illustration, by Fritz Wegner,Dawu Yu

The default separator is a `,` - if you prefer to use `and` then change the prompt like this:

    surfer in space, intricate detail, airbrush painting, illustration, by {2$$ and $$__artists/illustrations/childrens_books__}

Note the spaces surrounding the `and`.
If you don't add them then your combination might look like:

    A mech-warrior in a post-apocalyptic settings by artist1andartist2

You don't need to stop at 2; the combination syntax allows you to choose any number of artists. For four artists, you write it like this:

    surfer in space, intricate detail, airbrush painting, illustration, by {4$$__artists/illustrations/childrens_books__}

You can provide a range, e.g.

    surfer in space, intricate detail, airbrush painting, illustration, by {2-4$$__artists/illustrations/childrens_books__}

Here dynamic prompts will choose 2, 3, or 4 artists.

# Tools for inspiration

## Magic Prompts

When you look at prompts that people post online, you will often notice several modifiers related to lighting, resolution, camera type etc.
When you're starting out, you might feel overwhelmed by these modifiers.
The magic prompt functionality is a fun way to add modifiers to your prompt automatically.
You can experiment, but a good way to start is to use a simple prompt, e.g.

    A mech-warrior in a post-apocalyptic setting.

These images are a little plain. Let's jazz them up with Magic Prompts.
Enable Magic Prompt and click generate. (Note, Magic Prompt uses a neural network to add these based on context.
The first time you use it, Dynamic Prompts will need to download it, which may take some time depending on the speed of your Internet connection.)

Here are some example prompts that I get when using Magic Prompt:

    A mech-warrior in a post-apocalyptic setting. Digital illustration, Artstation. 8k resolution, Concept art, Detailed digital art

    A mech-warrior in a post-apocalyptic setting. Detailed digital art by greg rutkowski, Thomas kinkade, Keith Parkinson, artstation, cgsociety, deviantart, 8k, HD

    A mech-warrior in a post-apocalyptic setting. realistic shaded lighting poster by Ilya Kuvshinov katsuhiro, magali villeneuve, artgerm, Jeremy Lipkin and Michael Garmash, Rob Rey and Kentarï¿½ Miura style, trending on art station

When I have a subject in mind but I'm not yet sure about how I want the final image to look, I usually play around with magic prompt until I find something I like. I then use the generated prompt and tune from there.

## I'm feeling lucky

Another way of getting inspiration is through the I'm feeling lucky function. Instead of using a neural network, I'm feeling lucky uses the search engine on [Lexica.art](http://lexica.art) to find prompts that match your input. Quality may vary, but it is also a fun way to explore the latent space.

Using `mech-warrior` as my prompt, I get the following:

    giant oversized battle robot mech in battle pose is giant baby on a village, wooden fence and tree remains in far background, hero pose, Cinematic focus, Polaroid photo, vintage, neutral colors, soft lights, foggy, natural mysterous intricate detailed grainy photo, by Steve Hanks, by Serov Valentin, by lisa yuskavage, by Andrei Tarkovsky

    giant oversized battle robot mech as giant baby on a village, Cinematic focus, Polaroid photo, vintage, neutral colors, soft lights, foggy, by Steve Hanks, by Serov Valentin, by lisa yuskavage, by Andrei Tarkovsky

    a detailed manga illustration character full body portrait of a dark haired cyborg anime man who has a red mechanical eye, trending on artstation, digital art, 4 k resolution, detailed, high quality, sharp focus, hq artwork, insane detail, concept art, character concept, character illustration, full body illustration, cinematic, dramatic lighting

Two points are worth noting.

Firstly, in contrast to Magic Prompt, I'm feeling lucky prompts don't necessary contain our search string.
This is because Lexica performs a semantic search on its prompts database. This means the prompt should be relevant, even if the string doesn't match.

Secondly, if you were to look for this prompt on the Lexica.art website, you wouldn't find the generated images.
This is because you almost certainly used different settings than the person who originally crafted the prompt.

## Attention grabber

Another way of adding a touch of variation to your images to by changing emphasis of various terms in the prompt.
Attention grabber randomly assigns emphasis to an existing prompt.
Starting with a previous I'm feeling lucky prompt:

    a detailed manga illustration character full body portrait of a dark haired cyborg anime man who has a red mechanical eye, trending on artstation, digital art, 4 k resolution, detailed, high quality, sharp focus, hq artwork, insane detail, concept art, character concept, character illustration, full body illustration, cinematic, dramatic lighting

We add randomly add emphasis. For these images, I kept the seed constant so that you can see the impact of changing emphasis without changing any other settings.

    a detailed manga illustration character full body portrait of a dark haired cyborg anime man who has a red mechanical eye, trending on artstation, digital art, 4 k resolution, detailed, high quality, sharp focus, hq artwork, insane detail, concept art, character concept, character illustration, (full body illustration:1.58), cinematic, dramatic lighting

    a detailed manga illustration character full body portrait of a dark haired cyborg anime man who has a red mechanical eye, trending on artstation, digital art, 4 k resolution, detailed, high quality, sharp focus, hq artwork, insane detail, concept art, character concept, character illustration, (full body illustration:1.49), cinematic, dramatic lighting

    a detailed manga illustration character full body portrait of a dark haired cyborg anime man who has a red mechanical eye, trending on artstation, digital art, 4 k resolution, detailed, high quality, sharp focus, hq artwork, insane detail, concept art, character concept, (character illustration:1.26), full body illustration, cinematic, dramatic lighting

These changes are far more subtle and can be helpful if you want to explore slight changes to your image.

# Conclusion

This tutorial has covered the basics. There are additional features to try out once you feel comfortable using the tool.
You can find a list of syntax examples [here](SYNTAX.md).
