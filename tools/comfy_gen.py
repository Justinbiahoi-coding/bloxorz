"""Text-to-image through a running ComfyUI server. Usage: python gen.py "prompt" out.png [width height seed]"""
import json
import os
import random
import shutil
import sys
import time
import urllib.request
from pathlib import Path

SERVER = 'http://127.0.0.1:8188'
NEGATIVE = os.environ.get('NEG', 'text, watermark, logo, blurry, lowres, deformed, people, characters, buildings, skyscraper, birds, airplane')


def graph(prompt, w, h, seed):
    return {
        '1': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': 'sd_xl_base_1.0.safetensors'}},
        '2': {'class_type': 'CLIPTextEncode', 'inputs': {'text': prompt, 'clip': ['1', 1]}},
        '3': {'class_type': 'CLIPTextEncode', 'inputs': {'text': NEGATIVE, 'clip': ['1', 1]}},
        '4': {'class_type': 'EmptyLatentImage', 'inputs': {'width': w, 'height': h, 'batch_size': 1}},
        '5': {'class_type': 'KSampler', 'inputs': {
            'model': ['1', 0], 'positive': ['2', 0], 'negative': ['3', 0], 'latent_image': ['4', 0],
            'seed': seed, 'steps': 25, 'cfg': 7.0, 'sampler_name': 'euler', 'scheduler': 'normal', 'denoise': 1.0}},
        '6': {'class_type': 'VAEDecode', 'inputs': {'samples': ['5', 0], 'vae': ['1', 2]}},
        '7': {'class_type': 'SaveImage', 'inputs': {'images': ['6', 0], 'filename_prefix': 'bloxorz'}},
    }


def call(path, data=None):
    req = urllib.request.Request(SERVER + path, data=json.dumps(data).encode() if data else None,
                                 headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req))


def main():
    prompt, out = sys.argv[1], Path(sys.argv[2])
    w, h = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (1024, 1024)
    seed = int(sys.argv[5]) if len(sys.argv) > 5 else random.randrange(2**31)
    pid = call('/prompt', {'prompt': graph(prompt, w, h, seed)})['prompt_id']
    while pid not in (hist := call('/history/' + pid)):
        time.sleep(2)
    img = hist[pid]['outputs']['7']['images'][0]
    src = Path(__file__).parent / 'output' / img.get('subfolder', '') / img['filename']
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, out)
    print('saved', out, 'seed', seed)


if __name__ == '__main__':
    main()
