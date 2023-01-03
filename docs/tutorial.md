Constructing good prompts for Stable Diffusion can be difficult, especially if you're trying to learn through trial and error. Dynamic Prompts is an extension for Automatic1111's webui that let's you test dozens or hundreds of prompts at the same time by making tweaks to your base prompt.

Let's see how this works.

Suppose you want to create images of a diamond ring, you might start with something like:

    A diamond ring set on a gold band.

What if we wanted an image of a platinum ring as well? We can using Dynamic Prompts variant syntax, e.g.

    A diamond ring set on a {gold|platinum} band.

If we enter this into the prompts box with Dynamic Prompts installed, the generated prompt would be one of:

    A diamond ring set on a gold band

and

    A diamond ring set on a platinum band

Gold comes in various varieties, let's add those as well:

    A diamond ring set on a {{rose|yellow|white} gold|platinum} band.

Notice how we nested a variant for the type of gold, i.e. `{rose|yellow|white}` inside the main variant. So now, when generating an image, one of the following prompts is created:

    A diamond ring set on a rose gold band
    A diamond ring set on a yellow gold band
    A diamond ring set on a whilte gold band
    A diamond ring set on a platinum band

Nesting variants can quickly make your prompt template hard to read. Luckily, Dymamic Prompts ignores whitespace so that we can change the prompt to:

    A diamond ring set on a {
        {rose|yellow|white} gold   # you can also add comments
        | platinum                 # which will be ignored by the DP parser
    } band

Of course, we're not limited to only one variant, we can add a little more variation like this:

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

That second prompt isn't grammatically correct, it doesn't really matter to Stable Diffusion, but if you prefer correct English, you can write something like:

    {A diamond|A ruby|An emerald} ring set on a {classic|thin|thick} 
    {
        {rose|yellow|white} gold
        | platinum
    }
    band

Notice that we added a variant to the type of stone. Now we are creating, diamond, emerald and ruby rings. What if we had a large number of gems that we would like to use in our rings? You can certainly add them as variants, but this may become cumbersome with a large number of variants. In this case we can use a wildcard.

First, we create a file called gems.txt
In it we add one variant per line, e.g.

diamond
ruby
emerald
...

We place this file inside the extension's wildcard folder. This can be found in extensions/sd-dynamic-prompts/wildcards

Now our prompt changes to:

    A __gems__ ring set on a {classic|thin|thick} 
    {
        {rose|yellow|white} gold
        | platinum
    }
    band

`__gems__` is a wildcard and will act as a variant the uses every gem in gems.txt. Note, the name of the wildcard is the same as the name of the file, i.e. gems.txt without the .txt at the end. We then add a double underscore `__` to the beginning and end of the wildcard. Neat!

Wildcard files can use all the same syntax that we can use in our prompts. To demonstrate this, let's create a new file called precious_metals.txt. Inside we add:

{rose|yellow|white} gold
platinum
silver

Move the file into the wildcards folder. Now our prompt looks like this:

    A __gems__ ring set on a {classic|thin|thick} __previous_metals__ band

We can now generate a large number of different rings. Let's create 10 images. Set the batch count to 10 and click generate. This is what we get.

Note, Dynamic Prompts generates random prompts that conform with our template. Let's count the total number of possible rings our template can generate:

    The gems file has 10 gems
    3 band thicknesses
    3 metals, although gold has 3 variants so we actually have 5 metals.

    The total number of potential prompts is  10 * 3 * 3 = 90 different prompts.

What if we wanted to generate all of them? In that case we change to combinatorial mode. In combinatorial mode, batch count is interpreted differently. In random mode, batch count represented the total number of prompts to generate, in combinatorial mode, it means AT MOST 10 prompts. If our template was simply A diamond ring set on a {gold|platinum} band, then regardless of what we set batch count to, Dynamic Prompts will only generate two prompts. On the other hand if your gems.txt and precious_metals.txt files were very long, say 50 gems and 20 metals, you could then generate 1000 differnt prompts. The reason for setting the upper bound is to prevent accidentally generating far more prompts than you expect.

== Wildcards ==
A well-designed wildcard library can be used as building blocks for creating great prompts, without having to reinvent the wheel everytime. Dynamic Prompts provides a large collection of wildcards that you can either use wholesale, or pick and choose files that you're interested in. You can see these collections in the Wildcards Manager tab.

The most interesting wildcards are those related to art and artists. It's a great way to explore different styles. In particular, you can choose multiple artists to influence the final output. So you can write a prompt like:

    A mech-warrior in a post-apocalytic setting by artist1 and artist2.

This is where a wildcard library comes in very handy. Try this prompt:

    A mech-warrior in a post-apocalyptic settings by __artists__ and __artists__

Here are some prompts that I get:
    A mech-warrior in a post-apocalyptic settings by __artists__ and __artists__
    A mech-warrior in a post-apocalyptic settings by __artists__ and __artists__
    A mech-warrior in a post-apocalyptic settings by __artists__ and __artists__

Dynamic Prompts has syntax to simplify this. Two automatically choose two artists, we use the variant syntax but prepend it with a `2$$`. Instead of a variant, this is a combination and look like this:

    A mech-warrior in a post-apocalyptic settings by {2$$__artists__}

That will produce:

    A mech-warrior in a post-apocalyptic settings by __artists__,__artists__
    A mech-warrior in a post-apocalyptic settings by __artists__,__artists__
    A mech-warrior in a post-apocalyptic settings by __artists__,__artists__

The default separator is a `,` - if you prefer to use `and` then change the prompt like this:

    A mech-warrior in a post-apocalyptic settings by {2$$ and $$__artists__}

note the spaces surrounding the `and`. If you don't add them then your combination might look like:

A mech-warrior in a post-apocalyptic settings by artist1andartist2

You don't need to stop at 2, combination syntax allows you to choose any number of artists. For four artists you write it like this:

    A mech-warrior in a post-apocalyptic settings by {4$$__artists__}

You can provide a range, e.g.

    A mech-warrior in a post-apocalyptic settings by {2-4$$__artists__}

Here dynamic prompts will choose 2, 3, or 4 artists.

Magic Prompts
=============

When you look at prompts that people post online, you will often notice a number of modifiers related to lighting, resolution, camera type etc. When you're starting out, you might feel overwhelmed by these modifiers. The magic prompt functionality is a fun way to automatically add modifiers to your prompt. You can experiment, but a good way to start is to use a very simple prompt, e.g. 

    A mech-warriour in a post-apocalyptic setting.

Enable Magic Prompt and click generate. (Note, Magic Prompt uses a neural network add these based on context. The first time you use it, Dynamic Prompts will need to download it which may take some time depending on the speed of your Internet connection.)

Here are some example prompts that I get when using Magic Prompt:

A mech-warrior in a post-apocalyptic settings by {2$$__artists__}
A mech-warrior in a post-apocalyptic settings by {2$$__artists__}
A mech-warrior in a post-apocalyptic settings by {2$$__artists__}

When I have a subject in mind but I'm not yet sure about how I want the final image to look, I usually play around with magic prompt until I find something I like. I then use the generated prompt and tune from there.

I'm feeling lucky
=================
Another way of getting inspiration is through the I'm feeling lucky function. Instead of using a neural network, I'm feeling lucky uses the search engine on Lexica.art to find prompts that match your input. Quality may vary, but it is also a fun way to explore the latent space.

Attention grabber
=================

