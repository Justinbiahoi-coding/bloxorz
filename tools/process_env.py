"""Turn the raw ComfyUI images for the intro scenery into game textures (numpy + Pillow, dev only).

    python tools/process_env.py <raw_dir> <Source/assets/textures>

backdrop_*.png  -> kept as is (painted panorama), edges faded so the arc's ends melt into the night
cloud_*.png     -> RGBA: alpha from brightness (clouds were drawn on black)
tex_*.png       -> seamless (half-offset blend), 512 px
window_*.png    -> 256 px
noise.png       -> film grain, generated
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

raw, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)


def seamless(img, size=512):
    a = np.asarray(img.convert('RGB').resize((size, size), Image.LANCZOS)).astype(np.float32)
    rolled = np.roll(a, (size // 2, size // 2), axis=(0, 1))
    t = np.linspace(0, 1, size)
    edge = np.minimum(t, 1 - t) * 2
    w = np.clip(np.minimum.outer(edge, edge) * 2.5, 0, 1)[..., None]
    return Image.fromarray((a * w + rolled * (1 - w)).astype(np.uint8))


for f in sorted(raw.glob('*.png')):
    img = Image.open(f)
    if f.name.startswith('backdrop'):
        a = np.asarray(img.convert('RGB')).astype(np.float32)
        a = a[: int(a.shape[0] * 0.8)]                         # drop the foreground snow banks
        a = a * np.array([0.78, 0.74, 0.98], np.float32) * 0.9  # teal -> the deep moonlit blue of the reference
        h, w, _ = a.shape
        x = np.linspace(0, 1, w)
        fade = np.clip(np.minimum(x, 1 - x) / 0.08, 0, 1)[None, :, None]
        night = np.array([12, 16, 34], np.float32)
        Image.fromarray((a * fade + night * (1 - fade)).astype(np.uint8)).save(out / f.name)
    elif f.name.startswith('cloud'):
        a = np.asarray(img.convert('RGB')).astype(np.float32)
        lum = a.max(axis=2)
        alpha = np.clip((lum - 55) / 120, 0, 1) ** 1.3 * 255
        rgba = np.dstack([np.clip(a * 1.15, 0, 255), alpha]).astype(np.uint8)
        Image.fromarray(rgba, 'RGBA').save(out / f.name)
    elif f.name.startswith('tex_'):
        t = seamless(img)
        if 'concrete_wall' in f.name:                          # night: darker, bluer concrete for the tower
            t = Image.fromarray((np.asarray(t).astype(np.float32) * np.array([0.42, 0.45, 0.56])).astype(np.uint8))
        t.save(out / f.name[4:])
    elif f.name.startswith('window'):
        w = img.convert('RGB').resize((256, 340), Image.LANCZOS)
        if 'dark' in f.name:
            w = Image.fromarray((np.asarray(w).astype(np.float32) * 0.45).astype(np.uint8))
        w.save(out / f.name)
    print('processed', f.name)

rng = np.random.default_rng(1)
grain = rng.normal(128, 40, (256, 256)).clip(0, 255).astype(np.uint8)
Image.fromarray(np.dstack([grain, grain, grain, np.full_like(grain, 255)]), 'RGBA').save(out / 'noise.png')
print('noise')
