# AI generated novel

Visual novel generated in realtime using Stable Diffusion and GPT-3

### Disclaimer
As this is a bit complicated to run, I won't publish any builds that you can just run and play, sorry.

### Preparations and running
1. Install and set up [Stable Diffusion web UI](https://github.com/AUTOMATIC1111/stable-diffusion-webui). Add `--api --enable-insecure-extension-access` to `COMMANDLINE_ARGS` in your running script.
2. Install `stable-diffusion-webui-rembg` extension ([repo](https://github.com/AUTOMATIC1111/stable-diffusion-webui-rembg)) through the extensions tab.
3. Download [this model](https://civitai.com/models/8124/a-zovya-rpg-artist-tools) (or maybe some other one), install it and choose it in the web ui. I didn't try the vanilla SD, it's probably really terrible.
4. Download and unpack the [Ren'Py SDK](https://www.renpy.org/)
5. Run Ren'Py SDK and note the project directory.
6. Go into the project directory and clone this repo: `git clone https://github.com/maximxlss/ai-vn`
7. Put your OpenAI token into the `game/ai_gen.py` file.
8. If you want, [generate some music](https://colab.research.google.com/drive/1fxGqfg96RBUvGxZ1XXN07s3DthrKUl4-?usp=sharing) (place it at `game/audio/music.wav`) or replace the internal GPT prompt in `game/ai_gen.py`.
9. Install python libraries by going into the cloned repository and running pip: `pip install --target game/python-packages -r requirements.txt`
10. Delete the `certifi` dependency (Ren'Py quirk, I think?): `rm -r game/python-packages/certifi*`
11. Run the game through Ren'Py SDK.
