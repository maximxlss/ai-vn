import functools
import os
from pathlib import Path
from threading import Thread
import time
from typing import Iterator, NamedTuple, Optional, Union
import openai
import json
from tenacity import retry, wait_random_exponential, stop_after_attempt
import requests
import base64


openai.api_key = "REPLACE THIS WITH YOUR API KEY"


@retry(wait=wait_random_exponential(min=10, max=40), stop=stop_after_attempt(4))
def chat_completion_request(
    messages, functions=None, function_call="auto", model="gpt-3.5-turbo-0613"
):
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        functions=functions,
        function_call=function_call,
    )
    return response


def pretty_print_conversation(messages):
    formatted_messages = []
    for message in messages:
        if message["role"] == "system":
            formatted_messages.append(f"system: {message['content']}\n")
        elif message["role"] == "user":
            formatted_messages.append(f"user: {message['content']}\n")
        elif message["role"] == "assistant" and message.get("function_call"):
            formatted_messages.append(f"assistant: {message['function_call']}\n")
        elif message["role"] == "assistant" and not message.get("function_call"):
            formatted_messages.append(f"assistant: {message['content']}\n")
        elif message["role"] == "function":
            formatted_messages.append(
                f"function ({message['name']}): {message['content']}\n"
            )
    for formatted_message in formatted_messages:
        print(formatted_message)


functions = [
    {
        "name": "draw_background",
        "description": "Draw the background sprite and clear the scene. You would need to draw the characters again after this.",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "The concise description of the background to draw.",
                },
            },
            "required": ["description"],
        },
    },
    {
        "name": "draw_character_sprite",
        "description": "Draw a character sprite.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "A unique and persistent name of the character.",
                },
                "description": {
                    "type": "string",
                    "description": "The concise description of the character to draw.",
                },
            },
            "required": ["name", "description"],
        },
    },
    {
        "name": "dialogue_phrase",
        "description": "Make a character say a phrase.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "A unique and persistent name of the character.",
                },
                "phrase": {
                    "type": "string",
                    "description": "The phrase they would say.",
                },
            },
            "required": ["name", "phrase"],
        },
    },
    {
        "name": "prompt_user",
        "description": "Prompt user for an action.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]

context = [
    {
        "role": "system",
        "content": "Act out a smart visual novel, which has no numerical stats and everything is based on reasoning. The first user message would specify the overall setting. Draw the background and the characters sprites, then add dialogue. User would be the main character. Don't add their sprite. After, the user would specify their actions in user messages.",
    }
]


base_width = 960
base_height = 540


sd_url = "http://localhost/sdapi/v1/txt2img"
sd_request = """{{
  "enable_hr": false,
  "denoising_strength": 0,
  "firstphase_width": 0,
  "firstphase_height": 0,
  "hr_scale": 2,
  "hr_upscaler": "string",
  "hr_second_pass_steps": 0,
  "hr_resize_x": 0,
  "hr_resize_y": 0,
  "hr_sampler_name": "string",
  "hr_prompt": "",
  "hr_negative_prompt": "",
  "prompt": "{prompt}",
  "styles": [],
  "seed": -1,
  "subseed": -1,
  "subseed_strength": 0,
  "seed_resize_from_h": -1,
  "seed_resize_from_w": -1,
  "sampler_name": "Euler a",
  "batch_size": 1,
  "n_iter": 1,
  "steps": 20,
  "cfg_scale": 7,
  "width": {width},
  "height": {height},
  "restore_faces": true,
  "tiling": false,
  "do_not_save_samples": false,
  "do_not_save_grid": false,
  "negative_prompt": "",
  "eta": 0,
  "s_min_uncond": 0,
  "s_churn": 0,
  "s_tmax": 0,
  "s_tmin": 0,
  "s_noise": 1,
  "override_settings": {{}},
  "override_settings_restore_afterwards": true,
  "script_args": [],
  "sampler_index": "Euler",
  "script_name": "",
  "send_images": true,
  "save_images": false,
  "alwayson_scripts": {{}}
}}"""

upscale_url = "http://localhost/sdapi/v1/extra-single-image"
upscale_request = """{{
  "resize_mode": 0,
  "show_extras_results": true,
  "gfpgan_visibility": 0,
  "codeformer_visibility": 1,
  "codeformer_weight": 0,
  "upscaling_resize": 2,
  "upscaling_resize_w": 512,
  "upscaling_resize_h": 512,
  "upscaling_crop": true,
  "upscaler_1": "R-ESRGAN 4x+",
  "upscaler_2": "None",
  "extras_upscaler_2_visibility": 0,
  "upscale_first": false,
  "image": "{image_base64}"
}}"""

rembg_url = "http://localhost/rembg"
rembg_request = """{{
  "input_image": "{image_base64}",
  "model": "u2net",
  "return_mask": false,
  "alpha_matting": false,
  "alpha_matting_foreground_threshold": 240,
  "alpha_matting_background_threshold": 10,
  "alpha_matting_erode_size": 10
}}"""


def in_thread(func=None):
    if func is None:
        return in_thread

    def runner(q, *args, **kwargs):
        result = func(*args, **kwargs)
        q.append(result)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        q = []
        t = Thread(target=runner, args=[q, *args], kwargs=kwargs)
        t.start()
        return q

    return wrapper


@in_thread
def generate_sd(prompt, width=base_width, height=base_height) -> str:
    response = requests.post(
        sd_url, sd_request.format(prompt=prompt, width=width, height=height)
    )
    return response.json()["images"][0]


@in_thread
def upscale_x2(image_base64) -> str:
    response = requests.post(
        upscale_url, upscale_request.format(image_base64=image_base64)
    )
    return response.json()["image"]


@in_thread
def rembg(image_base64) -> str:
    response = requests.post(rembg_url, rembg_request.format(image_base64=image_base64))
    return response.json()["image"]


@in_thread
def generate_next(user_message: Optional[str] = None) -> dict:
    if user_message:
        context.append({"role": "user", "content": user_message})
    while len(context) > 7000:
        context.pop(2)
    response = chat_completion_request(context, functions)
    response_message = response["choices"][0]["message"]
    context.append(response_message)
    return response_message


class PhraseAction(NamedTuple):
    author_name: str
    content: str


class DrawBackgroundAction(NamedTuple):
    filename: str


class DrawCharacterAction(NamedTuple):
    name: str
    filename: str


class PromptAction(NamedTuple):
    pass


class Error(NamedTuple):
    message: str


def generate_next_data(
    user_message: Optional[str] = None, base_dir: str = ""
) -> Iterator[
    Union[
        None, str, PhraseAction, DrawBackgroundAction, DrawCharacterAction, PromptAction
    ]
]:
    try:
        yield "Asking GPT..."
        response = generate_next(user_message)
        while len(response) == 0:
            yield None
        response = response[0]

        print(response)

        if "function_call" in response:
            function_name = response["function_call"]["name"]
            args = json.loads(response["function_call"]["arguments"])

            if function_name == "draw_background":
                prompt_hash = hash(args["description"].strip())
                filename = f"background{prompt_hash}.png"
                if not Path(filename).exists():
                    yield "Generating a background: " + args["description"]
                    prompt = (
                        "masterpiece, best quality, light novel background, no humans, standing on the ground, "
                        + args["description"]
                    )
                    base64_data = generate_sd(prompt)
                    while len(base64_data) == 0:
                        yield None
                    base64_data = base64_data[0]
                    yield "upscaling"
                    base64_data = upscale_x2(base64_data)
                    while len(base64_data) == 0:
                        yield None
                    base64_data = base64_data[0]
                    img = base64.b64decode(base64_data)
                    path = os.path.join(base_dir, filename)
                    with open(path, "wb") as f:
                        f.write(img)
                yield DrawBackgroundAction(filename)
            elif function_name == "draw_character_sprite":
                prompt_hash = hash(args["description"].strip())
                filename = f"sprite{prompt_hash}.png"
                if not Path(filename).exists():
                    yield f"Generating {args['name']}: {args['description']}"
                    prompt = (
                        "masterpiece, best quality, full body, portait, visual novel sprite, looking at camera, plain background, "
                        + args["description"]
                    )
                    base64_data = generate_sd(prompt, width=300, height=500)
                    while len(base64_data) == 0:
                        yield None
                    base64_data = base64_data[0]
                    yield "upscaling"
                    base64_data = upscale_x2(base64_data)
                    while len(base64_data) == 0:
                        yield None
                    base64_data = base64_data[0]
                    yield "removing the background"
                    base64_data = rembg(base64_data)
                    while len(base64_data) == 0:
                        yield None
                    base64_data = base64_data[0]
                    img = base64.b64decode(base64_data)
                    path = os.path.join(base_dir, filename)
                    with open(path, "wb") as f:
                        f.write(img)
                yield DrawCharacterAction(args["name"], filename)
            elif function_name == "dialogue_phrase":
                yield PhraseAction(args["name"], args["phrase"])
            elif function_name == "prompt_user":
                yield PromptAction()
            else:
                yield f"GPT tried to call nonexistent function {function_name}"
        else:
            yield PhraseAction("Narrator", response["content"])
    except Exception as e:
        yield Error(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    prompt = input("Input a theme: ")

    while True:
        if prompt:
            data_generator = generate_next_data(prompt)
            prompt = None
        else:
            data_generator = generate_next_data()
        data = next(data_generator)
        while data is None:
            time.sleep(1.0)
            data = next(data_generator)
        print(data)
        class_name = data.__class__.__name__
        if isinstance(data, PhraseAction):
            print(data.author_name + ":", data.content)
        elif isinstance(data, DrawBackgroundAction):
            pass
        elif isinstance(data, DrawCharacterAction):
            pass
        elif isinstance(data, PromptAction):
            prompt = input("Input an action: ")
        else:
            print("unexpected type returned")
