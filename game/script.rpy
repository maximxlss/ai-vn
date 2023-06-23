# The script of the game goes in this file.

# Declare characters used by this game. The color argument colorizes the
# name of the character.

define e = Character("Eileen")


# The game starts here.


init python:
    import ai_gen


label start:
    play music "music.wav"

    $ base_dir = renpy.loader.get_path("images")
    $ images = {}
    $ prompt = renpy.input("Input a theme:")

    while True:
        if prompt:
            $ data_generator = ai_gen.generate_next_data(prompt, base_dir=base_dir)
            $ prompt = None
        else:
            $ data_generator = ai_gen.generate_next_data(base_dir=base_dir)
        $ data = next(data_generator)
        while data is None or isinstance(data, str):
            if isinstance(data, str):
                $ renpy.show("loading", at_list=[Transform(ypos=0.9)], what=Text(data))
            pause 1.0
            $ data = next(data_generator)
        $ renpy.hide("loading")
        $ print(data)
        $ class_name = data.__class__.__name__
        if isinstance(data, ai_gen.PhraseAction):
            $ renpy.say(data.author_name, data.content)
        elif isinstance(data, ai_gen.DrawBackgroundAction):
            $ images = {}
            $ renpy.scene()
            $ img = Image(data.filename)
            $ renpy.show("bg", what=img)
        elif isinstance(data, ai_gen.DrawCharacterAction):
            $ img = Image(data.filename)
            $ images[data.name] = img
            python:
                step = 1 / (len(images) + 1)
                for x, key in zip(range(1, len(images) + 1), images):
                    renpy.show(key, at_list=[Transform(xanchor=0.5, xpos=x * step, yalign=1.0)], what=images[key])
            $ renpy.show(data.name, what=img)
        elif isinstance(data, ai_gen.PromptAction):
            $ prompt = renpy.input("Input an action:")
        elif isinstance(data, ai_gen.Error):
            $ renpy.say(narrator, "Error occured:\n" + data.message)
        else:
            $ print("unexpected type returned")

    return
